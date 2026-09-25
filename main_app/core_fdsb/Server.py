# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later
# -*- coding: utf-8 -*-

# main_app/core_fdsb/Server.py

import discord
from discord.ext import commands
import os
import json
import asyncio
import threading
import time
import flet as ft

from main_app.core_fdsb.FDScript import run_script
from main_app.core_fdsb.FDCore import set_vars_dir, set_bot_start_time
from main_app.langs.translations import Translations

from main_app.core_fdsb.server_FDScript.prefix_manager import PrefixManager, prefix_manager
from main_app.core_fdsb.server_FDScript.flet_permissions import request_flet_permissions
from main_app.core_fdsb.server_FDScript.fgs_service import (
    STATE_WORKING, STATE_SYNCING, STATE_ERROR,
    set_language as _fgs_set_language,
    set_flet_page, send_flet_notification, ensure_background_mode,
    schedule_on_flet_loop, set_fgs_state,
    start_background_mode, stop_background_mode,
    update_android_status_notification,
)

_current_lang = 'ar'

def set_language(lang: str) -> None:
    global _current_lang
    if lang in Translations.translations:
        _current_lang = lang
    _fgs_set_language(lang)

def get_language() -> str:
    return _current_lang

def _t(key: str, **kwargs) -> str:
    text = Translations.get(key, _current_lang)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

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

_STATUS_DISCORD_STATE = {
    'online': discord.Status.online,
    'idle': discord.Status.idle,
    'dnd': discord.Status.dnd,
    'invisible': discord.Status.invisible,
}

_STATUS_ACTIVITY_TYPE = {
    'playing': discord.ActivityType.playing,
    'listening': discord.ActivityType.listening,
    'watching': discord.ActivityType.watching,
    'competing': discord.ActivityType.competing,
}

_STATUS_LOOP_UNIT_SECONDS = {
    'second': 1,
    'minute': 60,
    'hour': 3600,
    'day': 86400,
}

_STATUS_LOOP_TIME_MIN_SECONDS = 12
_STATUS_POLL_IDLE_SECONDS = 15

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
    status_text = (entry.get('status') or '').strip()
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

_client = None
_thread = None
_loop = None
_stopping = False
_vars_dir_path = ''
_status_task = None

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

def _get_bot_image(bot_dir: str) -> str:
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
                image = data.get('image')
                if image:
                    return str(image)
            except Exception:
                pass
    return ''

def _make_bot(bot_dir: str, bot_image: str = ''):
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
        send_flet_notification(_t('server_status_online', name=bot.user))

        _notify_state_change(True)
        await asyncio.sleep(1)
        await update_android_status_notification(str(bot.user), online=True, bot_image=bot_image)
        set_fgs_state(STATE_WORKING)

        global _status_task
        if _status_task is None or _status_task.done():
            _status_task = bot.loop.create_task(_status_rotator(bot, bot_dir))
        scripts = prefix_manager.get_event_scripts_with_arg("$onBotOnline")
        if scripts:
            from main_app.core_fdsb.event_FDScripts.onBotOnline import handle_event as handle_bot_online
            for script_text, channel_id in scripts:
                try:
                    await handle_bot_online(bot, script_text, channel_id)
                except Exception:
                    pass

    @bot.event
    async def on_disconnect():
        set_fgs_state(STATE_ERROR, "انقطع الاتصال" if _current_lang == 'ar' else "Disconnected")

    @bot.event
    async def on_resumed():
        set_fgs_state(STATE_WORKING)

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
            set_fgs_state(STATE_ERROR)

    @bot.event
    async def on_member_join(member):
        scripts = prefix_manager.get_event_scripts("$onJoined")
        if not scripts:
            return
        from main_app.core_fdsb.event_FDScripts.onJoined import handle_event
        for script_text in scripts:
            try:
                await handle_event(member, bot, script_text)
            except Exception:
                pass

    @bot.event
    async def on_member_remove(member):
        scripts = prefix_manager.get_event_scripts("$onLeave")
        if not scripts:
            return
        from main_app.core_fdsb.event_FDScripts.onLeave import handle_event
        for script_text in scripts:
            try:
                await handle_event(member, bot, script_text)
            except Exception:
                pass

    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        left_channel = before.channel if before.channel != after.channel else None
        joined_channel = after.channel if before.channel != after.channel else None
        if left_channel is not None:
            scripts = prefix_manager.get_event_scripts("$onVoiceLeave")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onVoiceLeave import handle_event
                for script_text in scripts:
                    try:
                        await handle_event(member, left_channel, bot, script_text)
                    except Exception:
                        pass
        if joined_channel is not None:
            scripts = prefix_manager.get_event_scripts("$onVoiceJoined")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onVoiceJoined import handle_event
                for script_text in scripts:
                    try:
                        await handle_event(member, joined_channel, bot, script_text)
                    except Exception:
                        pass

    @bot.event
    async def on_message(message):
        if message.type in _BOOST_MESSAGE_TYPES:
            scripts = prefix_manager.get_event_scripts("$onBoostServer")
            if scripts:
                from main_app.core_fdsb.event_FDScripts.onBoostServer import handle_event
                for script_text in scripts:
                    try:
                        await handle_event(message, bot, script_text)
                    except Exception:
                        pass
            return
        if message.author.bot:
            try:
                from main_app.core_fdsb.event_FDScripts.onBotMessage import handle_event as handle_bot_message
                await handle_bot_message(message, bot, prefix_manager._bot_events_dir)
            except Exception:
                pass
            return

        set_fgs_state(STATE_SYNCING)
        always_scripts = prefix_manager.get_event_scripts("$alwaysReply")
        if always_scripts:
            try:
                from main_app.core_fdsb.event_FDScripts.alwaysReply import handle_event as handle_always_reply
                for script_text in always_scripts:
                    await handle_always_reply(message, bot, script_text)
            except Exception:
                pass
        try:
            from main_app.core_fdsb.event_FDScripts.messageContains import handle_event as handle_message_contains
            await handle_message_contains(message, bot, prefix_manager._bot_events_dir)
        except Exception:
            pass
        try:
            from main_app.core_fdsb.event_FDScripts.messageContainsAll import handle_event as handle_message_contains_all
            await handle_message_contains_all(message, bot, prefix_manager._bot_events_dir)
        except Exception:
            pass

        # ── تشغيل جميع السكربتات المتطابقة بالتتابع الزمني من الأقدم للأحدث ──
        matching_scripts = prefix_manager.get_scripts_by_message(message.content)
        if matching_scripts:
            for script_text in matching_scripts:
                try:
                    await run_script(message, bot, script_text)
                except Exception as e:
                    print(f"[Server] Error executing script: {e}")
            return

        await bot.process_commands(message)

    return bot

def _runner(token: str):
    global _loop, _client, _stopping
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    try:
        _loop.run_until_complete(_client.start(token))
    except Exception as e:
        print(f"[Runner Error] {e}")
        set_fgs_state(STATE_ERROR, str(e))
    finally:
        _stopping = False
        _client = None
        _notify_state_change(False)

def start_bot(bot_dir: str) -> bool:
    global _client, _thread, _stopping, _vars_dir_path
    if _stopping:
        return False
    if _client and not _client.is_closed():
        return True
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
    bot_image = _get_bot_image(bot_root)
    _client = _make_bot(bot_root, bot_image)
    _thread = threading.Thread(target=_runner, args=(token,), daemon=True)
    _thread.start()
    schedule_on_flet_loop(start_background_mode('FDSB Server', bot_image))
    return True

def stop_bot() -> None:
    global _stopping, _status_task
    if _stopping:
        return
    if _client is None or _client.is_closed():
        return
    _stopping = True

    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_client.close(), _loop)
    if _status_task and not _status_task.done():
        _status_task.cancel()
    _status_task = None
    _notify_state_change(False)
    send_flet_notification(_t('server_status_stopped'))
    schedule_on_flet_loop(stop_background_mode())