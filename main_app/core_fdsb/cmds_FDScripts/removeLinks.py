# cmds_FDScripts/removeLinks.py
import discord
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    ctx.remove_links = True
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    ctx.remove_links = True
    ctx.log_event("removeLinks → links will be removed from the bot's message")