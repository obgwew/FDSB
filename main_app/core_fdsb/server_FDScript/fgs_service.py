# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later
# -*- coding: utf-8 -*-
# main_app/core_fdsb/server_FDScript/fgs_service.py

import os
import sys
import asyncio
from datetime import datetime
import flet as ft

from main_app.langs.translations import Translations

try:
    from flet_android_notifications import FletAndroidNotifications
except ImportError:
    FletAndroidNotifications = None

try:
    import flet_permission_handler as fph
except ImportError:
    fph = None

_current_lang = 'ar'

def set_language(lang: str) -> None:
    global _current_lang
    if lang in Translations.translations:
        _current_lang = lang

def _t(key: str, **kwargs) -> str:
    text = Translations.get(key, _current_lang)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

# ══════════════════════════════════════════════════════════════
# States
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

_FGS_NOTIFICATION_ID = 101
_FGS_MAX_SECONDS = 5 * 3600 + 50 * 60

_fgs_timeout_task = None
_fgs_bot_name = ''
_fgs_bot_image = ''
_fgs_start_time = None

# ══════════════════════════════════════════════════════════════
# Flet page / notifications
# ══════════════════════════════════════════════════════════════
def set_flet_page(page: ft.Page):
    global _flet_page
    _flet_page = page
    ensure_background_mode(page)

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
    return False

def ensure_background_mode(page: ft.Page):
    global _android_notifications, _wakelock, _permission_handler, _flet_session_loop
    if not _is_android():
        return
    try:
        _flet_session_loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            _flet_session_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
    if _android_notifications is None and FletAndroidNotifications is not None:
        try:
            _android_notifications = FletAndroidNotifications()
        except Exception as e:
            print(f"[Background] Notifications init error: {e}")
    if _wakelock is None:
        try:
            _wakelock = ft.Wakelock()
        except Exception as e:
            print(f"[Background] Wakelock unavailable: {e}")
    if _permission_handler is None and fph is not None:
        try:
            _permission_handler = fph.PermissionHandler()
            if hasattr(page, 'services') and _permission_handler not in page.services:
                page.services.append(_permission_handler)
        except Exception as e:
            print(f"[Background] PermissionHandler init error: {e}")

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

# ══════════════════════════════════════════════════════════════
# Foreground service 
# ══════════════════════════════════════════════════════════════
async def _push_fgs_notification(notifications, title: str, image_path: str = ""):
    fgs_types = ["data_sync"]
    kwargs = dict(
        notification_id=_FGS_NOTIFICATION_ID,
        title=title,
        body=_t('fgs_state_working'),
        foreground_service_types=fgs_types,
        start_type="start_sticky",
        ongoing=True,
        visibility="public",
        auto_cancel=False,
        silent=True,
        only_alert_once=True,
        show_when=True,
        uses_chronometer=True,
        chronometer_count_down=False,
        when=_fgs_start_time if _fgs_start_time else datetime.now(),
    )
    if image_path and os.path.isfile(image_path):
        kwargs['large_icon'] = image_path
        kwargs['large_icon_type'] = 'file_path'
    await notifications.start_foreground_service(**kwargs)

def set_fgs_state(state: str, detail: str = ""):
    pass

async def _fgs_timeout_loop():
    try:
        await asyncio.sleep(_FGS_MAX_SECONDS)
        global _fgs_running
        if _fgs_running:
            print("[FGS] Reached safe limit (5h50m). Stopping foreground service.")
            await stop_android_foreground_service()
            send_flet_notification(_t('fgs_limit_reached'))
    except asyncio.CancelledError:
        pass

async def start_android_foreground_service(bot_name: str, bot_image: str = ""):
    global _fgs_running, _fgs_timeout_task, _fgs_bot_name, _fgs_bot_image, _fgs_start_time
    if not _is_android():
        return
    notifications = _android_notifications
    if not notifications:
        return
    title = bot_name or "FDSB Bot Server"
    _fgs_bot_name = title
    _fgs_bot_image = bot_image or ''
    _fgs_start_time = datetime.now()

    try:
        if hasattr(notifications, 'request_permissions'):
            await notifications.request_permissions()
        await request_background_permissions()
        _fgs_running = True
        await _push_fgs_notification(notifications, title, _fgs_bot_image)
        if _fgs_timeout_task and not _fgs_timeout_task.done():
            _fgs_timeout_task.cancel()
        _fgs_timeout_task = asyncio.create_task(_fgs_timeout_loop())
    except Exception as e:
        print(f"[FGS] start failed: {e}")
        send_flet_notification(_t('fgs_start_failed', error=e))

async def stop_android_foreground_service():
    global _fgs_running, _fgs_timeout_task, _fgs_start_time
    if not _is_android():
        return
    notifications = _android_notifications
    if not notifications:
        return
    _fgs_running = False
    _fgs_start_time = None
    if _fgs_timeout_task and not _fgs_timeout_task.done():
        _fgs_timeout_task.cancel()
    _fgs_timeout_task = None
    try:
        await notifications.stop_foreground_service()
    except Exception as e:
        print(f"[FGS] stop failed: {e}")

# ══════════════════════════════════════════════════════════════
# Wakelock + combined start/stop used by local_server.start_bot/stop_bot
# ══════════════════════════════════════════════════════════════
async def _enable_wakelock():
    w = _wakelock
    if w is None:
        return
    try:
        await w.enable()
    except Exception:
        pass

async def _disable_wakelock():
    w = _wakelock
    if w is None:
        return
    try:
        await w.disable()
    except Exception:
        pass

async def start_background_mode(bot_name: str, bot_image: str = ""):
    await _enable_wakelock()
    await start_android_foreground_service(bot_name, bot_image)

async def stop_background_mode():
    await _disable_wakelock()
    await stop_android_foreground_service()

async def update_android_status_notification(bot_name: str, online: bool, bot_image: str = ""):
    if online:
        schedule_on_flet_loop(start_background_mode(bot_name, bot_image))
    else:
        schedule_on_flet_loop(stop_background_mode())