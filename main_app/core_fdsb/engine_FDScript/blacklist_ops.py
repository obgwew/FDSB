# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/blacklist_ops.py

import re
import discord

from .errors import FDLogicError, FDAbortScript, _send_error

_USER_MENTION_RE = re.compile(r"^<@!?(\d+)>$")
_ROLE_MENTION_RE = re.compile(r"^<@&(\d+)>$")


def parse_blacklist_args(args: list[str], ctx) -> tuple[list[str], str]:
    if len(args) == 1:
        raw_targets = [args[0]]
        custom_error = ""
    else:
        raw_targets = args[:-1]
        custom_error = ctx.resolve(args[-1]).strip()

    targets = []
    for raw in raw_targets:
        resolved = ctx.resolve(raw).strip()
        if not resolved:
            continue
        for part in resolved.split(","):
            cleaned = part.strip()
            if cleaned:
                targets.append(cleaned)

    return targets, custom_error


def check_user_blocked(targets: list[str], author: discord.User | discord.Member | None) -> tuple[bool, str]:
    if not author:
        return False, ""

    author_id = str(author.id)
    author_name = author.name.lower()
    author_display = getattr(author, "display_name", "").lower()
    author_global = getattr(author, "global_name", "") or ""
    author_global = author_global.lower()

    for target in targets:
        m = _USER_MENTION_RE.match(target)
        t_id = m.group(1) if m else (target if target.isdigit() else None)

        if t_id is not None and t_id == author_id:
            return True, f"{author.name} ({author_id})"

        t_lower = target.lower()
        if t_lower in (author_name, author_display, author_global):
            return True, f"{author.name} ({author_id})"

    return False, ""


def check_role_blocked(targets: list[str], member: discord.Member | None) -> tuple[bool, str]:
    if not member or not hasattr(member, "roles"):
        return False, ""

    member_roles = member.roles

    for target in targets:
        m = _ROLE_MENTION_RE.match(target)
        t_id = m.group(1) if m else (target if target.isdigit() else None)
        t_lower = target.lower()

        for role in member_roles:
            if t_id is not None and str(role.id) == t_id:
                return True, f"{role.name} ({role.id})"
            if role.name.lower() == t_lower:
                return True, f"{role.name} ({role.id})"

    return False, ""


def check_server_blocked(targets: list[str], guild: discord.Guild | None) -> tuple[bool, str]:
    if not guild:
        return False, ""

    guild_id = str(guild.id)
    guild_name = guild.name.lower()

    for target in targets:
        if target.isdigit() and target == guild_id:
            return True, f"{guild.name} ({guild_id})"
        if target.lower() == guild_name:
            return True, f"{guild.name} ({guild_id})"

    return False, ""


async def enforce_blacklist(
    cmd_name: str,
    is_blocked: bool,
    matched_info: str,
    custom_error: str,
    ctx,
    default_err_text: str,
) -> None:
    if not is_blocked:
        ctx.log_event(f"{cmd_name} → ✓ Passed")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()

    if custom_error:
        sent = await dest.send(custom_error)
        ctx.last_bot_message = sent
        ctx.log_event(f"{cmd_name} → Blocked [{matched_info}]. Custom error sent.")
    else:
        ctx.log_event(f"{cmd_name} → Blocked [{matched_info}]. Default error sent.")
        await _send_error(dest, FDLogicError(default_err_text))

    ctx.log_event(f"{cmd_name} → Aborting script execution.")
    raise FDAbortScript()