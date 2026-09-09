#cmds_FDScripts/joinSplitOut.py
import discord
from FDScript import ExecutionContext, Command, FDSyntaxError

def _process_join(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 1:
        ctx._abort_with_error(FDSyntaxError(
            "`$joinSplitOut` requires 1 argument: `$joinSplitOut[separator]`"
        ))

    separator = ctx.resolve(args[0])
    split_data = getattr(ctx, "split_out", [])
    return separator.join(split_data)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process_join(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result = _process_join(args, ctx)
    ctx.text_buffer += result
    ctx.log_event(f"joinSplitOut → output: '{result}'")