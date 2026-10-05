# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# cmds_FDScripts/cooldown.py
import re
import time
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDAbortScript, _send_error,
    _cooldowns,
)

def _humanize_remaining(seconds: float) -> str:
    total = max(0, round(seconds))

    units = (
        ("Day", 86400),
        ("Hour", 3600),
        ("Minute", 60),
        ("Second", 1),
    )

    for name, size in units:
        if total >= size or size == 1:
            amount = total // size
            return f"{amount} {name}{'' if amount == 1 else 's'}"

    return "0 Seconds"


_DISCORD_TS_RE = re.compile(r"<t:(?:%time%|\{time\})(?::([tTdDfFR]))?>")


def _get_user_id(ctx: ExecutionContext) -> int | str:
    if ctx.interaction is not None:
        return ctx.interaction.user.id
    if ctx.message is not None and getattr(ctx.message, "author", None):
        return ctx.message.author.id
    if getattr(ctx, "member", None) is not None:
        return ctx.member.id
    if ctx.builtins.get("authorID"):
        try:
            return int(ctx.builtins["authorID"])
        except ValueError:
            return ctx.builtins["authorID"]
    return "unknown_user"


def _get_command_scope(ctx: ExecutionContext, cmd: Command) -> str:
    if hasattr(ctx, "command_name") and ctx.command_name:
        return str(ctx.command_name)
    if hasattr(ctx, "script_id") and ctx.script_id:
        return str(ctx.script_id)
    if ctx.interaction is not None and getattr(ctx.interaction, "data", None):
        name = ctx.interaction.data.get("name") or ctx.interaction.data.get("custom_id")
        if name:
            return f"slash_{name}"
    if ctx.message and getattr(ctx.message, "content", None):
        parts = ctx.message.content.split()
        if parts:
            return parts[0].lower()
    return f"cmd_{cmd.line_no or 'global'}"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 1 or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$cooldown` requires at least a time — "
            "example: `$cooldown[10s]` or `$cooldown[10s; Please wait!]`"
        ))
        return

    time_str = ctx.resolve(args[0]).strip()
    
    error_msg = None
    if len(args) >= 2:
        raw_error = ";".join(args[1:])
        error_msg = ctx.resolve(raw_error).strip()
        if not error_msg:
            error_msg = None

    match = re.match(r"^(\d+(?:\.\d+)?)\s*([smhd])?$", time_str.lower())
    if not match:
        await _send_error(ch, FDLogicError(
            f"`$cooldown` — invalid time format: `{time_str}`. "
            "Use numbers followed by s (seconds), m (minutes), h (hours), or d (days)."
        ))
        return

    amount_str, unit = match.groups()
    unit = unit or 's'
    multiplier = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
    cooldown_seconds = float(amount_str) * multiplier

    current_time = time.time()
    user_id = _get_user_id(ctx)
    scope_id = _get_command_scope(ctx, cmd)

    cooldown_key = (user_id, scope_id)

    if len(_cooldowns) > 2000:
        expired_keys = [k for k, exp in _cooldowns.items() if current_time >= exp]
        for k in expired_keys:
            _cooldowns.pop(k, None)

    if cooldown_key in _cooldowns:
        expiry = _cooldowns[cooldown_key]
        if current_time < expiry:
            remaining = expiry - current_time

            if error_msg:
                time_display = _humanize_remaining(remaining)
                expiry_epoch = int(round(expiry))

                def _ts_sub(m: "re.Match[str]") -> str:
                    fmt = m.group(1) or "R"
                    return f"<t:{expiry_epoch}:{fmt}>"

                formatted_error = _DISCORD_TS_RE.sub(_ts_sub, error_msg)
                formatted_error = (
                    formatted_error
                    .replace("{time}", time_display)
                    .replace("%time%", time_display)
                )

                ctx.stop_typing()
                dest = await ctx.get_dest()
                sent = await dest.send(formatted_error)
                if sent is not None:
                    ctx.last_bot_message = sent

            ctx.log_event(f"cooldown → user {user_id} blocked ({remaining:.1f}s remaining) on [{scope_id}]")
            raise FDAbortScript()

    _cooldowns[cooldown_key] = current_time + cooldown_seconds
    ctx.log_event(f"cooldown → set {time_str} for user {user_id} on [{scope_id}]")