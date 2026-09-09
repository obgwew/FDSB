# cmds_FDScripts/cooldown.py
import re
import time
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDAbortScript, _send_error,
    _cooldowns,
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


def _humanize_remaining(seconds: float) -> str:
    """Format remaining cooldown time the same way BDFD's %time% does, e.g. '27 Seconds'."""
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

    return "0 Seconds"  # unreachable, safety net


_DISCORD_TS_RE = re.compile(r"<t:(?:%time%|\{time\})(?::([tTdDfFR]))?>")


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 1:
        await _send_error(ch, FDLogicError(
            "`$cooldown` requires at least a time — "
            "example: `$cooldown[10s]` or `$cooldown[10s; Please wait!]`"
        ))
        return

    time_str  = ctx.resolve(args[0]).strip()
    error_msg = ctx.resolve(args[1]).strip() if len(args) >= 2 and args[1].strip() else None

    match = re.match(r"^(\d+)([smhd])$", time_str.lower())
    if not match:
        await _send_error(ch, FDLogicError(
            f"`$cooldown` — invalid time format: `{time_str}`. "
            "Use numbers followed by s (seconds), m (minutes), h (hours), or d (days)."
        ))
        return

    amount_str, unit = match.groups()
    cooldown_seconds = int(amount_str) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]

    current_time = time.time()
    user_id      = ctx.message.author.id

    script_id = "global"
    if hasattr(ctx, "script_id"):
        script_id = ctx.script_id
    elif hasattr(ctx, "command_name"):
        script_id = ctx.command_name
    elif ctx.message and ctx.message.content:
        script_id = ctx.message.content.split()[0]

    cooldown_key = (user_id, script_id, cmd.raw)

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
                ctx.last_bot_message = sent

            ctx.log_event(f"cooldown → user {user_id} blocked ({remaining:.1f}s remaining) on [{cmd.raw}]")
            raise FDAbortScript()

    _cooldowns[cooldown_key] = current_time + cooldown_seconds
    ctx.log_event(f"cooldown → set {time_str} for user {user_id} on [{cmd.raw}]")