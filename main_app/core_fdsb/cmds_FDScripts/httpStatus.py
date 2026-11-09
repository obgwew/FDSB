# cmds_FDScripts/httpStatus.py
import discord
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return str(getattr(ctx, "http_status", "0"))

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result = str(getattr(ctx, "http_status", "0"))
    ctx.text_buffer += result