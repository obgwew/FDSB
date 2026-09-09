# cmds_FDScripts/wait.py
import asyncio
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, _send_error
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$wait` requires a time argument — example: `$wait[5s]`"
        ))
        return

    resolved_text = "".join(ctx.resolve(arg) for arg in args).strip()

    match = re.match(r"^(\d+)([smhd])$", resolved_text.lower())
    if not match:
        await _send_error(ch, FDLogicError(
            f"`$wait` — invalid time format: `{resolved_text}`. "
            "Use numbers followed by s (seconds), m (minutes), h (hours), or d (days)."
        ))
        return

    amount_str, unit = match.groups()
    amount = int(amount_str)

    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = amount * multipliers[unit]

    ctx.log_event(f"wait → strictly freezing script execution for {resolved_text} ({seconds} seconds)...")

    try:
        await asyncio.sleep(seconds)
        
        ctx.log_event(f"wait → freeze finished, resuming script execution")
        
    except Exception as ex:
        ctx.log_event(f"warning: unexpected error during $wait freeze: `{ex}`")