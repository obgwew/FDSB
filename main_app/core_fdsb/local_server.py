# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/core_fdsb/local_server.py 

import discord
from discord.ext import commands
import json
import os
import sys
import asyncio
import threading
import time
import flet as ft 

try:
    from flet_android_notifications import FletAndroidNotifications
except ImportError:
    FletAndroidNotifications = None

from main_app.core_fdsb.FDScript import run_script
from main_app.core_fdsb.FDCore   import set_vars_dir, set_bot_start_time

# ══════════════════════════════════════════════════════════════
#  Canonical event prefixes (single source of truth)
# ══════════════════════════════════════════════════════════════

EVENT_PREFIXES: set[str] = {
    '$onJoined',
    '$onLeave',
    '$onInteraction',
    '$onVoiceJoined',
    '$onVoiceLeave',
    '$alwaysReply',
    '$messageContains',
    '$messageContainsAll',
    '$onBotOnline',
    '$onBotMessage',
    '$onBoostServer',
}

_BOOST_MESSAGE_TYPES = {
    discord.MessageType.premium_guild_subscription,
    discord.MessageType.premium_guild_tier_1,
    discord.MessageType.premium_guild_tier_2,
    discord.MessageType.premium_guild_tier_3,
}

# ══════════════════════════════════════════════════════════════
#  Status Bot — presence rotation
# ══════════════════════════════════════════════════════════════

_STATUS_DISCORD_STATE = {
    'online':    discord.Status.online,
    'idle':      discord.Status.idle,
    'dnd':       discord.Status.dnd,
    'invisible': discord.Status.invisible,
}

_STATUS_ACTIVITY_TYPE = {
    'playing':    discord.ActivityType.playing,
    'listening':  discord.ActivityType.listening,
    'watching':   discord.ActivityType.watching,
    'competing':  discord.ActivityType.competing,
}

_STATUS_LOOP_UNIT_SECONDS = {
    'second': 1,
    'minute': 60,
    'hour':   3600,
    'day':    86400,
}

_STATUS_LOOP_TIME_MIN_SECONDS = 12
_STATUS_POLL_IDLE_SECONDS = 15

# ══════════════════════════════════════════════════════════════
#  PrefixManager 
# ══════════════════════════════════════════════════════════════

class PrefixManager:
    def __init__(self):
        self._bot_commands_dir = ''
        self._bot_events_dir = ''  

    def set_bot_dir(self, bot_dir: str):
        abs_dir = os.path.abspath(bot_dir)
        if os.path.basename(abs_dir).lower() == 'bot_files':
            bot_root = os.path.dirname(abs_dir)
        else:
            bot_root = abs_dir
        self._bot_commands_dir = os.path.join(bot_root, 'bot_commands')
        self._bot_events_dir = os.path.join(bot_root, 'bot_events') 

    def get_event_scripts(self, event_name: str) -> list[str]:
        results: list[str] = []
        if not os.path.isdir(self._bot_events_dir):
            return results

        for fname in sorted(os.listdir(self._bot_events_dir)):
            fpath = os.path.join(self._bot_events_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                first_line = content.split('\n')[0].strip().replace(" ", "").upper()
                if first_line.startswith("#PREFIX:"):
                    prefix_part = first_line.replace("#PREFIX:", "").split('[')[0]
                    if prefix_part == event_name.upper():
                        results.append(content)
            except Exception:
                pass
        return results

    def get_event_scripts_with_arg(self, event_name: str) -> list[tuple[str, str | None]]:
        results: list[tuple[str, str | None]] = []
        if not os.path.isdir(self._bot_events_dir):
            return results

        for fname in sorted(os.listdir(self._bot_events_dir)):
            fpath = os.path.join(self._bot_events_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                raw_first_line = content.split('\n')[0].strip()
                if raw_first_line.upper().startswith("#PREFIX:"):
                    prefix_body = raw_first_line.split(":", 1)[1].strip()
                    bstart = prefix_body.find('[')
                    bend = prefix_body.rfind(']')
                    prefix_name = (prefix_body[:bstart] if bstart != -1 else prefix_body).strip().upper()

                    if prefix_name == event_name.upper():
                        arg = None
                        if bstart != -1 and bend != -1 and bend > bstart:
                            arg = prefix_body[bstart + 1:bend].strip()
                        results.append((content, arg))
            except Exception:
                pass
        return results

    def get_script_by_message(self, message_content: str) -> str | None:
        if not os.path.isdir(self._bot_commands_dir):
            return None

        for fname in os.listdir(self._bot_commands_dir):
            fpath = os.path.join(self._bot_commands_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    continue
                
                first_line = content.split('\n')[0].strip()
                if first_line.upper().startswith("#PREFIX:"):
                    prefix = first_line.split(":", 1)[1].strip()
                    after = message_content.strip()[len(prefix):]
                    if message_content.strip().startswith(prefix) and (not after or after[0].isspace()):
                        return content
            except Exception:
                pass
        return None

# ─────────────────────────────────────────────────────────────
#  setting up the bot 
# ─────────────────────────────────────────────────────────────

_client          = None
_thread          = None
_loop            = None
_stopping        = False
_vars_dir_path   = ''
_status_task     = None
prefix_manager   = PrefixManager()
_flet_page       = None  

# ══════════════════════════════════════════════════════════════
#  State Listeners
# ══════════════════════════════════════════════════════════════
_state_listeners: list = []

def register_state_listener(callback):
    if callback not in _state_listeners:
        _state_listeners.append(callback)

def _notify_state_change(is_online: bool):
    for listener in list(_state_listeners):
        try:
            listener(is_online)
        except Exception:
            pass

def get_vars_dir() -> str:
    return _vars_dir_path

def _get_token(bot_dir: str) -> str:
    possible_paths = [
        os.path.join(bot_dir, 'config.json'),
        os.path.join(bot_dir, 'bot_files', 'config.json'),
        os.path.join(os.path.dirname(bot_dir), 'config.json'),
        os.path.join(os.path.dirname(bot_dir), 'bot_files', 'config.json'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                token = data.get('token') or data.get('TOKEN') or data.get('bot_token')
                if token:
                    return str(token)
            except Exception:
                pass
    return ''

def _load_status_config(bot_dir: str) -> dict | None:
    possible_paths = [
        os.path.join(bot_dir, 'bot_files', 'status_config.json'),
        os.path.join(bot_dir, 'status_config.json'),
        os.path.join(os.path.dirname(bot_dir), 'bot_files', 'status_config.json'),
        os.path.join(os.path.dirname(bot_dir), 'status_config.json'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return None

def _build_status_activity(entry: dict):
    activity_type = (entry.get('activity_type') or 'playing').strip().lower()
    status_text   = (entry.get('status') or '').strip()

    if activity_type == 'streaming':
        url = (entry.get('stream_url') or '').strip()
        if not url:
            return None
        return discord.Streaming(name=status_text or 'Live', url=url)

    if not status_text:
        return None

    activity_enum = _STATUS_ACTIVITY_TYPE.get(
        activity_type, discord.ActivityType.playing
    )
    return discord.Activity(type=activity_enum, name=f"● {status_text}")

async def _status_rotator(bot, bot_dir: str):
    try:
        while not bot.is_closed():
            config = _load_status_config(bot_dir)

            if not config or not config.get('enabled'):
                await asyncio.sleep(_STATUS_POLL_IDLE_SECONDS)
                continue

            discord_status = _STATUS_DISCORD_STATE.get(
                (config.get('status') or 'online').strip().lower(),
                discord.Status.online,
            )

            raw_entries = config.get('entries') or []
            entries = [
                e for e in raw_entries
                if (e.get('status') or '').strip()
                or (
                    (e.get('activity_type') or '').strip().lower() == 'streaming'
                    and (e.get('stream_url') or '').strip()
                )
            ]

            loop_unit = (config.get('loop_unit') or 'second').strip().lower()
            try:
                loop_time = int(config.get('loop_time') or 30)
            except (TypeError, ValueError):
                loop_time = 30
            interval = max(
                loop_time * _STATUS_LOOP_UNIT_SECONDS.get(loop_unit, 1),
                _STATUS_LOOP_TIME_MIN_SECONDS,
            )

            if not entries:
                try:
                    await bot.change_presence(status=discord_status, activity=None)
                except Exception:
                    pass
                await asyncio.sleep(_STATUS_POLL_IDLE_SECONDS)
                continue

            for entry in entries:
                if bot.is_closed():
                    return

                activity = _build_status_activity(entry)
                try:
                    await bot.change_presence(
                        status=discord_status,
                        activity=activity,
                    )
                except Exception:
                    pass

                await asyncio.sleep(interval)

    except asyncio.CancelledError:
        pass

# ══════════════════════════════════════════════════════════════
#  Flet Notifications
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

# ══════════════════════════════════════════════════════════════
#  Android Background Mode & Services (Android 15+ Optimized)
# ══════════════════════════════════════════════════════════════

_android_notifications = None
_wakelock = None
_flet_session_loop = None
_fgs_running = False

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

def _schedule_on_flet_loop(coro):
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
    global _android_notifications, _wakelock, _flet_session_loop
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

async def start_android_foreground_service(bot_name: str):
    global _fgs_running
    if not _is_android():
        return

    notifications = _android_notifications
    if not notifications:
        return

    title = bot_name or "FDSB Bot Server"
    body = "السيرفر قيد التشغيل في الخلفية ومحمي من انقطاع الشبكة"
    start_time_ms = int(time.time() * 1000)

    fgs_types = ["remote_messaging", "data_sync", "special_use"]

    try:
        if hasattr(notifications, 'request_permissions'):
            await notifications.request_permissions()

        try:
            await notifications.start_foreground_service(
                notification_id=101,
                title=title,
                body=body,
                foreground_service_types=fgs_types,
                start_type="start_sticky",
                ongoing=True,
                visibility="public",
                auto_cancel=False,
                silent=True,
                show_when=True,
                uses_chronometer=True,
                timestamp=start_time_ms,
            )
        except TypeError:
            try:
                await notifications.start_foreground_service(
                    notification_id=101,
                    title=title,
                    body=body,
                    foreground_service_types=fgs_types,
                    start_type="start_sticky",
                    ongoing=True,
                    visibility="public",
                    auto_cancel=False,
                    silent=True,
                    chronometer=True,
                    when=start_time_ms,
                )
            except TypeError:
                await notifications.start_foreground_service(
                    notification_id=101,
                    title=title,
                    body=body,
                    foreground_service_types=fgs_types,
                    start_type="start_sticky",
                    ongoing=True,
                    visibility="public",
                    auto_cancel=False,
                    silent=True,
                )
        _fgs_running = True
    except Exception as e:
        print(f"[FGS] start failed: {e}")
        send_flet_notification(f"⚠️ فشل تشغيل خدمة الخلفية: {e}")

async def stop_android_foreground_service():
    global _fgs_running
    if not _is_android():
        return

    notifications = _android_notifications
    if not notifications:
        return

    try:
        await notifications.stop_foreground_service()
        _fgs_running = False
    except Exception as e:
        print(f"[FGS] stop failed: {e}")

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

async def _start_background_mode(bot_name: str):
    await _enable_wakelock()
    await start_android_foreground_service(bot_name)

async def _stop_background_mode():
    await _disable_wakelock()
    await stop_android_foreground_service()

async def update_android_status_notification(bot_name: str, online: bool):
    if online:
        _schedule_on_flet_loop(_start_background_mode(bot_name))
    else:
        _schedule_on_flet_loop(_stop_background_mode())

# ══════════════════════════════════════════════════════════════
# event_FDScripts
# ══════════════════════════════════════════════════════════════

def _make_bot(bot_dir: str):
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    intents.presences = True
    
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"[Bot] Logged in successfully as: {bot.user}")
        set_bot_start_time(time.time())
        send_flet_notification(f"البوت نشط الآن: {bot.user}")
        
        _notify_state_change(True)

        await asyncio.sleep(1)
        await update_android_status_notification(str(bot.user), online=True)

        global _status_task
        if _status_task is None or _status_task.done():
            _status_task = bot.loop.create_task(_status_rotator(bot, bot_dir))

        scripts = prefix_manager.get_event_scripts_with_arg("$onBotOnline")
        if scripts:
            from main_app.core_fdsb.event_FDScripts.onBotOnline import handle_event as handle_bot_online
            for script_text, channel_id in scripts:
                try: await handle_bot_online(bot, script_text, channel_id)
                except Exception: pass
    
    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            return
        try:
            await interaction.response.defer()
        except Exception:
            pass
        from main_app.core_fdsb.event_FDScripts.onInteraction import handle_event
        try:
            await handle_event(interaction, bot, custom_id, prefix_manager._bot_events_dir)
        except Exception as e:
            print(f"[Bot] Error executing $onInteraction event: {e}")

    @bot.event
    async def on_member_join(member):
        scripts = prefix_manager.get_event_scripts("$onJoined")
        if not scripts: return
        from main_app.core_fdsb.event_FDScripts.onJoined import handle_event
        for script_text in scripts:
            try: await handle_event(member, bot, script_text)
            except Exception: pass

    @bot.event
    async def on_member_remove(member):
        scripts = prefix_manager.get_event_scripts("$onLeave")
        if not scripts: return
        from main_app.core_fdsb.event_FDScripts.onLeave import handle_event
        for script_text in scripts:
            try: await handle_event(member, bot, script_text)
            except Exception: pass

    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        left_channel = before.channel if before.channel != after.channel else None
        joined_channel = after.channel if before.channel != after.channel else None

        if left_channel is not None:
            scripts = prefix_manager.get_event_scripts("$onVoiceLeave")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onVoiceLeave import handle_event
                for script_text in scripts:
                    try: await handle_event(member, left_channel, bot, script_text)
                    except Exception: pass

        if joined_channel is not None:
            scripts = prefix_manager.get_event_scripts("$onVoiceJoined")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onVoiceJoined import handle_event
                for script_text in scripts:
                    try: await handle_event(member, joined_channel, bot, script_text)
                    except Exception: pass

    @bot.event
    async def on_message(message):
        if message.type in _BOOST_MESSAGE_TYPES:
            scripts = prefix_manager.get_event_scripts("$onBoostServer")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onBoostServer import handle_event
                for script_text in scripts:
                    try: await handle_event(message, bot, script_text)
                    except Exception: pass
            return

        if message.author.bot:
            try:
                from main_app.core_fdsb.event_FDScripts.onBotMessage import handle_event as handle_bot_message
                await handle_bot_message(message, bot, prefix_manager._bot_events_dir)
            except Exception: pass
            return

        always_scripts = prefix_manager.get_event_scripts("$alwaysReply")
        if always_scripts:
            try:
                from main_app.core_fdsb.event_FDScripts.alwaysReply import handle_event as handle_always_reply
                for script_text in always_scripts:
                    await handle_always_reply(message, bot, script_text)
            except Exception: pass

        try:
            from main_app.core_fdsb.event_FDScripts.messageContains import handle_event as handle_message_contains
            await handle_message_contains(message, bot, prefix_manager._bot_events_dir)
        except Exception: pass

        try:
            from main_app.core_fdsb.event_FDScripts.messageContainsAll import handle_event as handle_message_contains_all
            await handle_message_contains_all(message, bot, prefix_manager._bot_events_dir)
        except Exception: pass

        script_text = prefix_manager.get_script_by_message(message.content)
        if script_text is not None:
            try: await run_script(message, bot, script_text)
            except Exception: pass
            return

        await bot.process_commands(message)

    return bot

# ══════════════════════════════════════════════════════════════
#  Threading
# ══════════════════════════════════════════════════════════════

def _runner(token: str):
    global _loop, _client, _stopping
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    
    try:
        _loop.run_until_complete(_client.start(token))
    except Exception as e:
        print(f"[Runner Error] {e}")
    finally:
        _stopping = False
        _client = None
        _notify_state_change(False)

def start_bot(bot_dir: str) -> bool:
    global _client, _thread, _stopping, _vars_dir_path

    if _stopping: return False
    if _client and not _client.is_closed(): return True

    token = _get_token(bot_dir)
    if not token: 
        _notify_state_change(False)
        return False

    prefix_manager.set_bot_dir(bot_dir)

    abs_bot_dir = os.path.abspath(bot_dir)
    if os.path.basename(abs_bot_dir).lower() == 'bot_files':
        bot_root = os.path.dirname(abs_bot_dir)
    else:
        bot_root = abs_bot_dir

    _vars_dir_path = os.path.join(bot_root, 'bot_vars')
    os.makedirs(_vars_dir_path, exist_ok=True)
    set_vars_dir(_vars_dir_path)

    _client = _make_bot(bot_root)
    _thread = threading.Thread(target=_runner, args=(token,), daemon=True)
    _thread.start()

    _schedule_on_flet_loop(_start_background_mode('FDSB Server'))
    return True

def stop_bot() -> None:
    global _stopping, _status_task
    if _stopping: return
    if _client is None or _client.is_closed(): return
    _stopping = True
    
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_client.close(), _loop)

    if _status_task and not _status_task.done():
        _status_task.cancel()
    _status_task = None

    _notify_state_change(False)
    send_flet_notification("تم إيقاف خدمة البوت.")
    _schedule_on_flet_loop(_stop_background_mode())

# ══════════════════════════════════════════════════════════════
#  Flet GUI Permissions (Android 13, 14, 15 Compatible)
# ══════════════════════════════════════════════════════════════

_permission_handler = None

async def request_flet_permissions(page: ft.Page):
    global _permission_handler
    if _permission_handler is None:
        _permission_handler = ft.PermissionHandler()
        page.overlay.append(_permission_handler)
        page.update()

    ph = _permission_handler

    try:
        if hasattr(ph, 'check_permission_async'):
            notif_status = await ph.check_permission_async(ft.PermissionType.NOTIFICATION)
            if notif_status != ft.PermissionStatus.GRANTED:
                await ph.request_permission_async(ft.PermissionType.NOTIFICATION)
        else:
            notif_status = ph.check_permission(ft.PermissionType.NOTIFICATION)
            if notif_status != ft.PermissionStatus.GRANTED:
                ph.request_permission(ft.PermissionType.NOTIFICATION)
    except Exception as e:
        print(f"[Permissions] Notification error: {e}")

    try:
        if hasattr(ph, 'check_permission_async'):
            battery_status = await ph.check_permission_async(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
            if battery_status != ft.PermissionStatus.GRANTED:
                await ph.request_permission_async(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
        else:
            battery_status = ph.check_permission(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
            if battery_status != ft.PermissionStatus.GRANTED:
                ph.request_permission(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
    except Exception as e:
        print(f"[Permissions] Battery optimization error: {e}")