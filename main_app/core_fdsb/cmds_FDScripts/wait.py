# cmds_FDScripts/wait.py
import asyncio
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError("`$wait` requires a time argument — example: `$wait[5s]`"))
        return

    resolved_text = "".join(ctx.resolve(arg) for arg in args).strip()
    match = re.match(r"^(\d+)([smhd])$", resolved_text.lower())
    if not match:
        await _send_error(ch, FDLogicError(f"`$wait` — invalid time format: `{resolved_text}`"))
        return

    amount_str, unit = match.groups()
    amount = int(amount_str)
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = amount * multipliers[unit]

    if hasattr(ctx, "text_buffer") and ctx.text_buffer.strip():
        channel = ch or getattr(ctx, "channel", None) or getattr(ctx.message, "channel", None)
        if channel:
            msg = await channel.send(ctx.text_buffer)
            ctx.last_bot_message = msg
            ctx.text_buffer = ""

    ctx.log_event(f"wait → freezing for {seconds}s...")
    await asyncio.sleep(seconds)