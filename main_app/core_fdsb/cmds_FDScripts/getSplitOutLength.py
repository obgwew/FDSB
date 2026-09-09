#cmds_FDScripts/getSplitOutLength.py
import discord
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    split_data = getattr(ctx, "split_out", [])
    return str(len(split_data))


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    split_data = getattr(ctx, "split_out", [])
    result = str(len(split_data))
    ctx.text_buffer += result
    ctx.log_event(f"getSplitOutLength → {result}")