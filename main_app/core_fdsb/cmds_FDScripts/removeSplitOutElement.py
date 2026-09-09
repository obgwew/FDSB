#cmds_FDScripts/removeSplitOutElement.py
import discord
from FDScript import ExecutionContext, Command, FDSyntaxError, FDLogicError

def _process_remove(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 1:
        ctx._abort_with_error(FDSyntaxError(
            "`$removeSplitOutElement` requires 1 argument: `$removeSplitOutElement[index]`"
        ))

    idx_raw = ctx.resolve(args[0]).strip()
    if not idx_raw.isdigit():
        ctx._abort_with_error(FDLogicError(
            f"`$removeSplitOutElement` — index must be a positive integer, got `{idx_raw}`"
        ))

    idx = int(idx_raw)
    split_data = getattr(ctx, "split_out", [])

    if idx < 1 or idx > len(split_data):
        ctx._abort_with_error(FDLogicError(
            f"`$removeSplitOutElement` — index `{idx}` out of range (1 to {len(split_data)})"
        ))

    split_data.pop(idx - 1)
    return ""


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process_remove(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    _process_remove(args, ctx)
    ctx.log_event("removeSplitOutElement executed successfully")