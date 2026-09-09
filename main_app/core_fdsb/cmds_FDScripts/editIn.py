# cmds_FDScripts/editIn.py
import asyncio
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$editIn` requires at least 2 arguments: `$editIn[time; newMessage]`"
        ))
        return

    time_str = ctx.resolve(args[0]).strip().lower()
    new_message = ctx.resolve(args[1]).strip()

    if not time_str:
        await _send_error(ch, FDLogicError("`$editIn` — Time argument cannot be empty."))
        return

    unit = time_str[-1]
    val_str = time_str[:-1]

    if unit not in ('s', 'm', 'h', 'd') or not val_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editIn` — Invalid time format '{time_str}'. Use numbers followed by s, m, h, or d (e.g., 5s, 10m)."
        ))
        return

    val = int(val_str)
    if unit == 's':
        seconds = val
    elif unit == 'm':
        seconds = val * 60
    elif unit == 'h':
        seconds = val * 3600
    else:
        seconds = val * 86400

    target_msg = getattr(ctx, "last_bot_message", None)

    if target_msg is None:
        await _send_error(ch, FDEnvironmentError(
            "`$editIn` — No previous bot message found. You must send a message before using this command."
        ))
        return

    await asyncio.sleep(seconds)

    try:
        await target_msg.edit(content=new_message)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editIn` — bot lacks permission to edit that message"
        ))
        return
    except discord.NotFound:
        ctx.log_event(f"editIn → message {target_msg.id} was deleted before the edit could be applied")
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDEnvironmentError(
            f"`$editIn` — failed to edit message `{target_msg.id}`: `{e}`"
        ))
        return

    ctx.log_event(f"editIn → edited message ID: {target_msg.id} after {seconds}s")