#cmds_FDScripts/cropText.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDSyntaxError,
    _send_error
)

def _process_crop(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(FDSyntaxError(
            "`$cropText` requires at least 2 arguments: `$cropText[text; max characters; (ending)]`"
        ))

    text = ctx.resolve(args[0])
    max_chars_raw = ctx.resolve(args[1]).strip()
    ending = ctx.resolve(args[2]) if len(args) > 2 else ""

    if not max_chars_raw.isdigit():
        ctx._abort_with_error(FDLogicError(
            f"`$cropText` — max characters (2nd arg) must be a non-negative integer, got `{max_chars_raw}`"
        ))

    max_chars = int(max_chars_raw)

    if len(text) > max_chars:
        return text[:max_chars] + ending
    return text


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process_crop(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result = _process_crop(args, ctx)
    ctx.text_buffer += result
    ctx.log_event(f"cropText → output length: {len(result)}")