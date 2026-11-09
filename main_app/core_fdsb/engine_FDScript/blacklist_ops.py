# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/blacklist_ops.py

import re
import discord

from .errors import FDLogicError, FDAbortScript, _send_error

_USER_MENTION_RE = re.compile(r"^<@!?(\d+)>$")
_ROLE_MENTION_RE = re.compile(r"^<@&(\d+)>$")


def _looks_like_target(text: str) -> bool:
    """True if `text` is purely a snowflake ID or a user/role mention (never a human message)."""
    t = text.strip()
    return bool(t) and (t.isdigit() or _USER_MENTION_RE.match(t) or _ROLE_MENTION_RE.match(t))


def parse_blacklist_args(args: list[str], ctx) -> tuple[list[str], str]:
    # Resolve every argument exactly once (nested $commands / variables expand here).
    resolved = [ctx.resolve(a).strip() for a in args]

    # The LAST argument is a custom error message, unless it is itself just an ID/mention
    # (so `[id1;id2]` blocks both instead of treating id2 as the message).
    if len(resolved) > 1 and not _looks_like_target(resolved[-1]):
        raw_targets, custom_error = resolved[:-1], resolved[-1]
    else:
        raw_targets, custom_error = resolved, ""

    targets = []
    for item in raw_targets:
        for part in item.split(","):
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

    # From here on the script MUST abort, whatever happens while notifying the user.
    # (A plain Exception escaping this function would be caught by the dispatcher,
    #  which reports it and then CONTINUES running the next commands.)
    try:
        ctx.stop_typing()
        dest = await ctx.get_dest()

        if custom_error:
            sent = await dest.send(custom_error)
            ctx.last_bot_message = sent
            ctx.log_event(f"{cmd_name} → Blocked [{matched_info}]. Custom error sent.")
        else:
            ctx.log_event(f"{cmd_name} → Blocked [{matched_info}]. Default error sent.")
            await _send_error(dest, FDLogicError(default_err_text))
    except FDAbortScript:
        raise
    except Exception as e:
        ctx.log_event(f"{cmd_name} → warning: could not send the blocked message: {e}")

    ctx.log_event(f"{cmd_name} → Aborting script execution.")
    raise FDAbortScript()