# cmds_FDScripts/title.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        index = 1
        if len(args) > 1:
            idx_str = ctx.resolve(args[1]).strip()
            if idx_str.isdigit():
                index = int(idx_str)
        ctx.get_embed_builder(index).title = ctx.resolve(args[0])
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) in (1, 2):
        index = 1
        if len(args) == 2:
            idx_str = ctx.resolve(args[1]).strip()
            if not idx_str.isdigit():
                await _send_error(ch, FDLogicError("`$title` index must be a number: $title[text;index]"))
                return
            index = int(idx_str)
        resolved_text = ctx.resolve(args[0])
        ctx.get_embed_builder(index).title = resolved_text
        ctx.log_event(f"title → {_truncate(resolved_text)!r} (index {index})")
    else:
        await _send_error(ch, FDLogicError("`$title` requires 1-2 arguments: $title[text;index (optional)]"))