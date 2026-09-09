# cmds_FDScripts/deletecommand.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    try:
        await ctx.message.delete()
        ctx.log_event("deletecommand → deleted")
    except discord.Forbidden:
        ctx.log_event("deletecommand → ✗ no permission")
        await _send_error(ch, FDEnvironmentError(
            "`$deletecommand` — bot lacks permission to delete messages in this channel"
        ))
    except discord.NotFound:
        ctx.log_event("deletecommand → ✗ message not found")