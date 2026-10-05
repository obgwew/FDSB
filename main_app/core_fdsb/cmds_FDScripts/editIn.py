# cmds_FDScripts/editIn.py
import asyncio
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDLogicError("`$editIn` requires at least 2 arguments: `$editIn[time; newMessage]`"))
        return

    time_str = ctx.resolve(args[0]).strip().lower()
    new_message = ctx.resolve(args[1]).strip()

    if not time_str or time_str[-1] not in ('s', 'm', 'h', 'd') or not time_str[:-1].isdigit():
        await _send_error(ch, FDLogicError(f"`$editIn` — Invalid time format '{time_str}'."))
        return

    unit = time_str[-1]
    val = int(time_str[:-1])
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    seconds = val * multipliers[unit]

    channel = ch or getattr(ctx, "channel", None) or getattr(ctx.message, "channel", None)

    target_msg = getattr(ctx, "last_bot_message", None)

    if target_msg is None:
        if hasattr(ctx, "text_buffer") and ctx.text_buffer.strip() and channel:
            target_msg = await channel.send(ctx.text_buffer)
            ctx.last_bot_message = target_msg
            ctx.text_buffer = ""
        else:
            await _send_error(channel, FDEnvironmentError("`$editIn` — No previous bot message found to edit."))
            return

    await asyncio.sleep(seconds)

    try:
        await target_msg.edit(content=new_message)
        ctx.log_event(f"editIn → edited message ID: {target_msg.id} after {seconds}s")
    except Exception as e:
        ctx.log_event(f"editIn error: {e}")