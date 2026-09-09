# cmds_FDScripts/switch.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(FDLogicError(
            "`$switch` requires at least 2 arguments: `$switch[item1; item2; ... ; index]`"
        ))
        return ""

    try:
        index = int(args[-1].strip())
    except ValueError:
        ctx._abort_with_error(FDLogicError(
            f"`$switch` — The last argument '{args[-1]}' must be a valid integer index."
        ))
        return ""

    items = args[:-1]

    if index < 1 or index > len(items):
        ctx._abort_with_error(FDLogicError(
            f"`$switch` — Index {index} is out of bounds. You only provided {len(items)} items."
        ))
        return ""

    return items[index - 1]

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$switch` requires at least 2 arguments: `$switch[item1; item2; ... ; index]`"
        ))
        return

    try:
        index = int(args[-1].strip())
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$switch` — The last argument '{args[-1]}' must be a valid integer index."
        ))
        return

    items = args[:-1]

    if index < 1 or index > len(items):
        await _send_error(ch, FDLogicError(
            f"`$switch` — Index {index} is out of bounds. You only provided {len(items)} items."
        ))
        return

    result = items[index - 1]

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"switch → {result} (index: {index})")