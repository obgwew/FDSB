# cmds_FDScripts/splitIn.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def _do_split(args: list[str], ctx: ExecutionContext) -> tuple[list[str] | None, str, str]:
    if len(args) < 2:
        return None, "`$splitIn` requires two arguments: `$splitIn[text; delimiter]`", ""

    text      = ctx.resolve(args[0])
    delimiter = ctx.resolve(args[1])

    if not delimiter:
        return None, "`$splitIn` — delimiter cannot be empty", delimiter

    parts = [part.strip() for part in text.split(delimiter)]
    ctx.split_result = parts
    return parts, "", delimiter


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    parts, err, _delim = _do_split(args, ctx)
    if parts is None:
        ctx.log_event(f"splitIn inline error: {err}")
        return ""

    ctx.log_event(f"splitIn (inline) → split into {len(parts)} part(s)")
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    parts, err, delimiter = _do_split(args, ctx)
    if parts is None:
        await _send_error(ch, FDLogicError(err))
        return

    ctx.log_event(f"splitIn → split into {len(parts)} part(s) using delimiter `{delimiter}`")