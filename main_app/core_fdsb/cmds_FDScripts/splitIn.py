# cmds_FDScripts/splitIn.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError,
    _send_error,
)


def _do_split(args: list[str], ctx: ExecutionContext) -> tuple[list[str] | None, Exception | None, str]:
    if len(args) < 2:
        return None, FDSyntaxError("`$splitIn` requires two arguments: `$splitIn[text; delimiter]`"), ""

    text = ctx.resolve(args[0])
    delimiter = ctx.resolve(args[1])

    if not delimiter:
        delimiter = " "

    parts = [part.strip() for part in text.split(delimiter)]
    ctx.split_result = parts
    ctx.split_out = parts

    return parts, None, delimiter


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    parts, err, _delim = _do_split(args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
        return ""

    ctx.log_event(f"splitIn (inline) → split into {len(parts)} part(s)")
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    parts, err, delimiter = _do_split(args, ctx)
    if err is not None:
        await _send_error(ch, err)
        return

    ctx.log_event(f"splitIn → split into {len(parts)} part(s) using delimiter `{delimiter}`")