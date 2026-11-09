# cmds_FDScripts/toLowercase.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error, _truncate,
)

_USAGE = "`$toLowercase` requires one argument: `$toLowercase[text]`"


def _compute(args: list[str], ctx: ExecutionContext) -> tuple[str | None, str | None]:
    if not args:
        return None, _USAGE
    return ";".join(ctx.resolve(arg) for arg in args).lower(), None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    result, error = _compute(args, ctx)
    if error is not None:
        ctx._abort_with_error(FDLogicError(error))
    return result or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result, error = _compute(args, ctx)
    if error is not None:
        await _send_error(ch, FDLogicError(error))
        return

    if not result:
        await _send_error(ch, FDLogicError(
            "`$toLowercase` — text cannot be empty"
        ))
        return

    ctx.stop_typing()
    sent = await ch.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"toLowercase → {_truncate(result)!r}")