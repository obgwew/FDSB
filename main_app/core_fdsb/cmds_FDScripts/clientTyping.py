# cmds_FDScripts/clientTyping.py
import discord
from FDScript import ExecutionContext, Command


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    ctx.start_typing(ch)
    ctx.log_event("clientTyping → started")