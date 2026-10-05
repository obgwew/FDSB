# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/discord_helpers.py

import re

import discord

from .errors import FDLogicError, FDRuntimeError, FDEnvironmentError, _send_error

async def _resolve_dm_target(
    target_str: str,
    ctx,
    ch: discord.abc.Messageable,
) -> discord.User | discord.Member | None:
    target_str = target_str.strip()
    mention_match = re.match(r'^<@!?(\d+)>$', target_str)
    if mention_match:
        user_id = int(mention_match.group(1))
    elif target_str.isdigit():
        user_id = int(target_str)
    else:
        await _send_error(ch, FDLogicError(
            f"`$dm` — invalid target: `{target_str}`.\n"
            f"Use a user ID or a mention (e.g. `<@123456789>`)."
        ))
        return None

    user = ctx.bot.get_user(user_id)
    if user is None:
        try:
            user = await ctx.bot.fetch_user(user_id)
        except discord.NotFound:
            await _send_error(ch, FDEnvironmentError(
                f"`$dm` — no user found with ID `{user_id}`"
            ))
            return None
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$dm` — failed to fetch user `{user_id}`: `{e.text}`"
            ))
            return None
    return user

_CHANNEL_TYPES: dict[str, type] = {
    "text":     discord.TextChannel,
    "voice":    discord.VoiceChannel,
    "category": discord.CategoryChannel,
    "forum":    discord.ForumChannel,
    "stage":    discord.StageChannel,
    "all":      None,
}

_PERMISSION_NAMES: set[str] = {
    "admin","manage_guild","manage_roles","manage_channels","manage_messages",
    "manage_webhooks","manage_nicknames","manage_emojis","manage_threads",
    "manage_events","kick_members","ban_members","moderate_members",
    "mention_everyone","send_messages","send_tts_messages","embed_links",
    "attach_files","read_message_history","use_external_emojis",
    "use_external_stickers","add_reactions","connect","speak","mute_members",
    "deafen_members","move_members","use_voice_activation","priority_speaker",
    "stream","view_channel","view_audit_log","view_guild_insights",
    "change_nickname","create_instant_invite","request_to_speak",
    "use_application_commands","use_embedded_activities",
}

def _resolve_permission(raw: str) -> discord.Permissions | None | bool:
    raw = raw.strip().lower()
    if not raw or raw == "all":
        return None
    if raw.isdigit():
        return discord.Permissions(int(raw))
    if raw in _PERMISSION_NAMES:
        return discord.Permissions(**{raw: True})
    return False
