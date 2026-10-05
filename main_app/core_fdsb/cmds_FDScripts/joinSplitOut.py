# cmds_FDScripts/joinSplitOut.py
import discord
from FDScript import ExecutionContext, Command, FDSyntaxError

def _process_join(args: list[str], ctx: ExecutionContext) -> str:
    split_data = getattr(ctx, "split_result", getattr(ctx, "split_out", None))

    if len(args) > 0 and args[0].strip():
        separator = ctx.resolve(args[0])
    else:
        separator = " "

    return separator.join(split_data)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process_join(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result = _process_join(args, ctx)
    
    ctx.text_buffer += result
    ctx.log_event(f"joinSplitOut → output: '{result}'")