# cmds_FDScripts/lineCount.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "0"
    text = ctx.resolve(args[0])
    return str(text.count(" "))


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$lineCount` requires 1 argument: $lineCount[message]"
        ))
        return

    text = ctx.resolve(args[0])
    count = text.count(" ")

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(str(count))
    ctx.last_bot_message = sent
    ctx.log_event(f"lineCount → {count} space(s) in {len(text)} char(s)")