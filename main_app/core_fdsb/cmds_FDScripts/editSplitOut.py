#cmds_FDScripts/editSplitOut.py
import discord
from FDScript import ExecutionContext, Command, FDSyntaxError, FDLogicError

def _process_edit(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(FDSyntaxError(
            "`$editSplitOut` requires 2 arguments: `$editSplitOut[index; value]`"
        ))

    idx_raw = ctx.resolve(args[0]).strip()
    new_value = ctx.resolve(args[1])

    if not idx_raw.isdigit():
        ctx._abort_with_error(FDLogicError(
            f"`$editSplitOut` — index must be a positive integer, got `{idx_raw}`"
        ))

    idx = int(idx_raw)
    split_data = getattr(ctx, "split_out", [])

    if idx < 1 or idx > len(split_data):
        ctx._abort_with_error(FDLogicError(
            f"`$editSplitOut` — index `{idx}` out of range (1 to {len(split_data)})"
        ))

    split_data[idx - 1] = new_value
    return ""


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process_edit(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    _process_edit(args, ctx)
    ctx.log_event("editSplitOut executed successfully")