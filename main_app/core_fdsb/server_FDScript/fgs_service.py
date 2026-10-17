# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/core_fdsb/server_FDScript/fgs_service.py

import os
import sys
import asyncio
from datetime import datetime
import flet as ft

from main_app.langs._translations import Translations

try:
    from flet_android_notifications import FletAndroidNotifications
except ImportError:
    FletAndroidNotifications = None

try:
    import flet_permission_handler as fph
except ImportError:
    fph = None


def _lang() -> str:
    from main_app.settings_app import get_current_lang
    return get_current_lang()


def set_language(lang: str) -> None:
    return None


def _t(key: str, **kwargs) -> str:
    text = Translations.get(key, _lang())
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

# ══════════════════════════════════════════════════════════════
# States / globals
# ══════════════════════════════════════════════════════════════
STATE_WORKING = "working"
STATE_SYNCING = "syncing"
STATE_ERROR   = "error"

_android_notifications = None
_wakelock = None
_permission_handler = None
_flet_page = None
_flet_session_loop = None
_fgs_running = False
# Serialises start/stop: the permission dialogs fire pause/resume lifecycle events
# that used to trigger a second concurrent start.
_fgs_lock = asyncio.Lock()

# Notification ids / channels
_FGS_NOTIFICATION_ID = 101
_LEAVE_NOTIFICATION_ID = 102
_LIMIT_NOTIFICATION_ID = 103
_DOWNLOAD_NOTIFICATION_ID = 104

_ALERT_CHANNEL_ID = "fdsb_alerts"
_SERVICE_CHANNEL_ID = "fdsb_service"
_DOWNLOAD_CHANNEL_ID = "fdsb_downloads"

# Android limits a dataSync foreground service to ~6h, stop slightly before it.
_FGS_MAX_SECONDS = 5 * 3600 + 50 * 60
# How long the "download finished" notification stays visible.
_DOWNLOAD_DONE_VISIBLE_MS = 4000

_bot_should_run = False
_app_in_background = False
# The "app is in background" alert is shown ONCE per bot session, never repeated.
_leave_notified = False
# Set when the 6h limit stopped the service; blocks silent auto-restarts.
_limit_reached = False

_fgs_timer_task = None
_download_dismiss_task = None
_fgs_bot_name = ''
_fgs_bot_image = ''
_fgs_start_time = None


def _title() -> str:
    return _fgs_bot_name or _t('fgs_default_title')


def set_flet_page(page: ft.Page):
    global _flet_page, _prev_lifecycle_handler
    _flet_page = page
    ensure_background_mode(page)
    try:
        current = getattr(page, 'on_app_lifecycle_state_change', None)
        if current is not _on_app_lifecycle_change:
            _prev_lifecycle_handler = current
            page.on_app_lifecycle_state_change = _on_app_lifecycle_change
    except Exception as e:
        print(f"[FGS] lifecycle hook failed: {e}")


def send_flet_notification(message: str):
    global _flet_page
    if _flet_page:
        try:
            snack = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_GREY_900,
                duration=4000,
            )
            if hasattr(_flet_page, 'open'):
                _flet_page.open(snack)
            elif hasattr(_flet_page, 'show_dialog'):
                _flet_page.show_dialog(snack)
            else:
                _flet_page.snack_bar = snack
                _flet_page.snack_bar.open = True
                _flet_page.update()
        except Exception:
            pass


def _is_android() -> bool:
    if _flet_page is not None and hasattr(_flet_page, 'platform'):
        try:
            plat = getattr(_flet_page.platform, 'value', str(_flet_page.platform))
            if str(plat).lower() == 'android':
                return True
        except Exception:
            pass
    return (
        hasattr(sys, 'getandroidapilevel')
        or 'ANDROID_ARGUMENT' in os.environ
        or os.environ.get('FLET_PLATFORM') == 'android'
    )


def schedule_on_flet_loop(coro) -> bool:
    global _flet_page, _flet_session_loop
    if _flet_page is not None and hasattr(_flet_page, 'run_task'):
        async def _wrapper():
            try:
                await coro
            except Exception as e:
                print(f"[FGS Task Error] {e}")
        try:
            _flet_page.run_task(_wrapper)
            return True
        except Exception:
            pass
    loop = _flet_session_loop
    if loop is not None and not loop.is_closed():
        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
            return True
        except RuntimeError:
            pass
    try:
        coro.close()
    except Exception:
        pass
    return False


def _attach_service(page: ft.Page, svc) -> None:
    """Flet services only work after they are added to page.services AND the page
    is updated; otherwise every method call on them fails."""
    try:
        if hasattr(page, 'services') and svc not in page.services:
            page.services.append(svc)
    except Exception as e:
        print(f"[Background] attach service failed: {e}")


def ensure_background_mode(page: ft.Page):
    global _android_notifications, _wakelock, _permission_handler, _flet_session_loop, _flet_page
    if page is None:
        return
    if _flet_page is None:
        _flet_page = page
    if not _is_android():
        return
    try:
        _flet_session_loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            _flet_session_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
    added = False
    if _android_notifications is None and FletAndroidNotifications is not None:
        try:
            _android_notifications = FletAndroidNotifications()
            _attach_service(page, _android_notifications)
            added = True
        except Exception as e:
            _android_notifications = None
            print(f"[Background] Notifications init error: {e}")
    if _wakelock is None:
        try:
            _wakelock = ft.Wakelock()
            _attach_service(page, _wakelock)
            added = True
        except Exception as e:
            _wakelock = None
            print(f"[Background] Wakelock unavailable: {e}")
    if _permission_handler is None and fph is not None:
        try:
            _permission_handler = fph.PermissionHandler()
            _attach_service(page, _permission_handler)
            added = True
        except Exception as e:
            print(f"[Background] PermissionHandler init error: {e}")
    if added:
        try:
            page.update()
        except Exception as e:
            print(f"[Background] page.update failed: {e}")

# ══════════════════════════════════════════════════════════════
# Permissions
# ══════════════════════════════════════════════════════════════
async def request_background_permissions() -> None:
    if not _is_android() or _permission_handler is None or fph is None:
        return

    try:
        notif_status = await _permission_handler.request(fph.Permission.NOTIFICATION)
        print(f"[Permissions] NOTIFICATION -> {getattr(notif_status, 'name', notif_status)}")
    except Exception as e:
        print(f"[Permissions] NOTIFICATION request failed: {e}")

    try:
        battery_status = await _permission_handler.get_status(
            fph.Permission.IGNORE_BATTERY_OPTIMIZATIONS
        )
        if battery_status is None or getattr(battery_status, "name", "") != "granted":
            battery_status = await _permission_handler.request(
                fph.Permission.IGNORE_BATTERY_OPTIMIZATIONS
            )
        print(f"[Permissions] IGNORE_BATTERY_OPTIMIZATIONS -> {getattr(battery_status, 'name', battery_status)}")
    except Exception as e:
        print(f"[Permissions] IGNORE_BATTERY_OPTIMIZATIONS request failed: {e}")


async def ensure_notification_permission() -> bool:
    """Ask for the POST_NOTIFICATIONS permission (Android 13+) if not granted yet."""
    if not _is_android():
        return True
    if _permission_handler is not None and fph is not None:
        try:
            status = await _permission_handler.get_status(fph.Permission.NOTIFICATION)
            if getattr(status, 'name', '') == 'granted':
                return True
            status = await _permission_handler.request(fph.Permission.NOTIFICATION)
            return getattr(status, 'name', '') == 'granted'
        except Exception as e:
            print(f"[Permissions] NOTIFICATION check failed: {e}")
    n = _android_notifications
    if n is not None:
        try:
            if await n.are_notifications_enabled():
                return True
            return bool(await n.request_permissions())
        except Exception as e:
            print(f"[Permissions] plugin notification permission failed: {e}")
    return False

# ══════════════════════════════════════════════════════════════
# Notification helpers
# ══════════════════════════════════════════════════════════════
async def _show_alert(notification_id: int, title: str, body: str):
    n = _android_notifications
    if n is None:
        return
    try:
        await n.show_notification(
            notification_id=notification_id,
            title=title,
            body=body,
            channel_id=_ALERT_CHANNEL_ID,
            channel_name=_t('fgs_alert_channel_name'),
            channel_description=_t('fgs_alert_channel_desc'),
            importance="high",
            play_sound=False,
            enable_vibration=False,
            auto_cancel=True,
            only_alert_once=True,
            visibility="public",
        )
    except Exception as e:
        print(f"[FGS] alert {notification_id} failed: {e}")


async def _cancel_alert(notification_id: int):
    n = _android_notifications
    if n is None:
        return
    try:
        await n.cancel(notification_id)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# Temporary download notification (wiki)
# ══════════════════════════════════════════════════════════════
async def _dismiss_download_later(delay: float):
    try:
        await asyncio.sleep(delay)
        await _cancel_alert(_DOWNLOAD_NOTIFICATION_ID)
    except asyncio.CancelledError:
        pass


async def show_download_notification(title: str, body: str, done: bool = False, page=None):
    """Temporary download notification.
    - While downloading: calling it again updates the SAME notification (live progress).
    - When done=True: it stays for a few seconds, then disappears by itself."""
    global _download_dismiss_task, _flet_page
    if page is not None and _flet_page is None:
        _flet_page = page
    if _android_notifications is None and _flet_page is not None:
        ensure_background_mode(_flet_page)
        # give the freshly attached native service a moment to mount
        await asyncio.sleep(0.3)
    n = _android_notifications
    if n is None or not _is_android():
        print(f"[FGS] download notification skipped (plugin={n is not None}, android={_is_android()})")
        return

    # A newer update always cancels a pending auto-dismiss.
    if _download_dismiss_task is not None and not _download_dismiss_task.done():
        _download_dismiss_task.cancel()
    _download_dismiss_task = None

    try:
        await n.show_notification(
            notification_id=_DOWNLOAD_NOTIFICATION_ID,
            title=title,
            body=body,
            channel_id=_DOWNLOAD_CHANNEL_ID,
            channel_name=_t('download_channel_name'),
            channel_description=_t('download_channel_desc'),
            importance="high",
            play_sound=False,
            enable_vibration=False,
            ongoing=not done,
            auto_cancel=True,
            only_alert_once=True,
            visibility="public",
            timeout_after=_DOWNLOAD_DONE_VISIBLE_MS if done else None,
        )
    except Exception as e:
        print(f"[FGS] download notification failed: {e}")
        return

    if done:
        # Fallback in case the OS ignores timeout_after.
        _download_dismiss_task = asyncio.create_task(
            _dismiss_download_later(_DOWNLOAD_DONE_VISIBLE_MS / 1000 + 0.5)
        )


async def cancel_download_notification():
    global _download_dismiss_task
    if _download_dismiss_task is not None and not _download_dismiss_task.done():
        _download_dismiss_task.cancel()
    _download_dismiss_task = None
    await _cancel_alert(_DOWNLOAD_NOTIFICATION_ID)

# ══════════════════════════════════════════════════════════════
# Foreground service (flet_android_notifications, native count-up chronometer)
# ══════════════════════════════════════════════════════════════
def set_fgs_state(state: str, detail: str = ""):
    pass


def is_fgs_running() -> bool:
    return _fgs_running


def _start_limit_task():
    global _fgs_timer_task
    if _fgs_timer_task and not _fgs_timer_task.done():
        _fgs_timer_task.cancel()
    _fgs_timer_task = asyncio.create_task(_fgs_limit_loop())


async def _fgs_limit_loop():
    """Waits until the ~6h Android limit (5h50m), then removes the timer
    notification and asks the user to restart the app."""
    try:
        await asyncio.sleep(_FGS_MAX_SECONDS)
        if not _fgs_running:
            return
        print("[FGS] Reached safe limit (5h50m). Stopping foreground service.")
        await _finish_by_limit()
    except asyncio.CancelledError:
        pass


async def _finish_by_limit():
    global _limit_reached
    _limit_reached = True
    # 1) stop the service (removes the count-up timer notification)
    await stop_android_foreground_service()
    await _cancel_alert(_FGS_NOTIFICATION_ID)
    await _cancel_alert(_LEAVE_NOTIFICATION_ID)
    # 2) tell the user to restart the app
    await _show_alert(
        _LIMIT_NOTIFICATION_ID,
        _title(),
        _t('fgs_limit_reached'),
    )


async def start_android_foreground_service(bot_name: str, bot_image: str = ""):
    async with _fgs_lock:
        await _start_android_foreground_service_locked(bot_name, bot_image)


async def _start_android_foreground_service_locked(bot_name: str, bot_image: str = ""):
    global _fgs_running, _fgs_bot_name, _fgs_bot_image, _fgs_start_time
    if not _is_android():
        return
    n = _android_notifications
    if n is None:
        print("[FGS] flet_android_notifications unavailable - bot will NOT survive leaving the app")
        return
    if _fgs_running:
        return
    title = bot_name or _title()
    _fgs_bot_name = title
    _fgs_bot_image = bot_image or _fgs_bot_image

    try:
        if not await ensure_notification_permission():
            print("[FGS] notification permission denied")
            send_flet_notification(_t('fgs_start_failed', error=_t('fgs_permission_denied')))
            return
        await request_background_permissions()

        _fgs_start_time = datetime.now()
        await n.start_foreground_service(
            notification_id=_FGS_NOTIFICATION_ID,
            title=title,
            body=_t('fgs_state_working'),
            foreground_service_types=["data_sync"],
            # Native count-up timer (Android Chronometer) starting from "now".
            when=_fgs_start_time,
            show_when=True,
            uses_chronometer=True,
            chronometer_count_down=False,
            channel_id=_SERVICE_CHANNEL_ID,
            channel_name=_t('fgs_service_channel_name'),
            channel_description=_t('fgs_service_channel_desc'),
            importance="low",
            play_sound=False,
            enable_vibration=False,
            ongoing=True,
            auto_cancel=False,
            silent=True,
            only_alert_once=True,
            visibility="public",
        )
        _fgs_running = True
        _start_limit_task()
    except Exception as e:
        _fgs_running = False
        _fgs_start_time = None
        print(f"[FGS] start failed: {e}")
        send_flet_notification(_t('fgs_start_failed', error=e))


async def stop_android_foreground_service():
    async with _fgs_lock:
        await _stop_android_foreground_service_locked()


async def _stop_android_foreground_service_locked():
    global _fgs_running, _fgs_timer_task, _fgs_start_time
    if not _is_android():
        return
    _fgs_running = False
    _fgs_start_time = None
    if (_fgs_timer_task and not _fgs_timer_task.done()
            and _fgs_timer_task is not asyncio.current_task()):
        _fgs_timer_task.cancel()
    _fgs_timer_task = None
    n = _android_notifications
    if n is None:
        return
    try:
        await n.stop_foreground_service()
    except Exception as e:
        print(f"[FGS] stop failed: {e}")

# ══════════════════════════════════════════════════════════════
# Leaving / returning to the app
# ══════════════════════════════════════════════════════════════
_LEAVING_STATES = {"pause", "hide", "detach"}
_RETURNING_STATES = {"resume", "show"}


def _on_app_lifecycle_change(e):
    state = getattr(e, 'state', None)
    name = str(getattr(state, 'value', state) or '').lower().split('.')[-1]
    if name in _LEAVING_STATES:
        schedule_on_flet_loop(_handle_user_leaving())
    elif name in _RETURNING_STATES:
        schedule_on_flet_loop(_handle_user_returning())
    if _prev_lifecycle_handler is not None:
        try:
            _prev_lifecycle_handler(e)
        except Exception:
            pass


async def _handle_user_leaving():
    global _app_in_background, _leave_notified
    already_in_background = _app_in_background
    _app_in_background = True
    if not _is_android() or not _bot_should_run or _limit_reached:
        return
    # pause/hide/detach can fire several times in a row -> ignore repeats.
    if already_in_background:
        return
    if not _fgs_running:
        await start_android_foreground_service(_title(), _fgs_bot_image)
    # The leave alert is sent only ONCE per bot session.
    if _leave_notified:
        return
    _leave_notified = True
    await _show_alert(
        _LEAVE_NOTIFICATION_ID,
        _title(),
        _t('fgs_background_notice') if _fgs_running else _t('fgs_background_unprotected'),
    )


async def _handle_user_returning():
    global _app_in_background
    _app_in_background = False
    if not _is_android():
        return
    await _cancel_alert(_LEAVE_NOTIFICATION_ID)
    await _cancel_alert(_LIMIT_NOTIFICATION_ID)
    if not _bot_should_run or _limit_reached:
        return
    if not _fgs_running:
        await start_android_foreground_service(_title(), _fgs_bot_image)

# ══════════════════════════════════════════════════════════════
# Wakelock + combined start/stop used by server.start_bot/stop_bot
# ══════════════════════════════════════════════════════════════
async def _enable_wakelock():
    w = _wakelock
    if w is None:
        return
    try:
        await w.enable()
    except Exception as e:
        print(f"[Background] wakelock enable failed: {e}")


async def _disable_wakelock():
    w = _wakelock
    if w is None:
        return
    try:
        await w.disable()
    except Exception as e:
        print(f"[Background] wakelock disable failed: {e}")


async def start_background_mode(bot_name: str, bot_image: str = ""):
    global _bot_should_run, _leave_notified, _limit_reached
    # A fresh start of the bot = a fresh session: reset the one-time alert
    # and the 6h limit flag, and clear the old "restart the app" notification.
    if not _bot_should_run:
        _leave_notified = False
    _limit_reached = False
    await _cancel_alert(_LIMIT_NOTIFICATION_ID)
    _bot_should_run = True
    await _enable_wakelock()
    await start_android_foreground_service(bot_name, bot_image)


async def stop_background_mode():
    global _bot_should_run, _leave_notified
    if not _bot_should_run and not _fgs_running:
        return
    _bot_should_run = False
    _leave_notified = False
    await _disable_wakelock()
    await stop_android_foreground_service()
    await _cancel_alert(_FGS_NOTIFICATION_ID)
    await _cancel_alert(_LEAVE_NOTIFICATION_ID)
    await _cancel_alert(_LIMIT_NOTIFICATION_ID)


async def update_android_status_notification(bot_name: str, online: bool, bot_image: str = ""):
    if online:
        schedule_on_flet_loop(start_background_mode(bot_name, bot_image))
    else:
        schedule_on_flet_loop(stop_background_mode())