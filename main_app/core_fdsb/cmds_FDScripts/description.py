# cmds_FDScripts/description.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        index = 1
        if len(args) > 1:
            idx_str = ctx.resolve(args[1]).strip()
            if idx_str.isdigit():
                index = int(idx_str)
        ctx.get_embed_builder(index).description = ctx.resolve(args[0])
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) in (1, 2):
        index = 1
        if len(args) == 2:
            idx_str = ctx.resolve(args[1]).strip()
            if not idx_str.isdigit():
                await _send_error(ch, FDLogicError("`$description` index must be a number: $description[text;index]"))
                return
            index = int(idx_str)
        resolved_text = ctx.resolve(args[0])
        ctx.get_embed_builder(index).description = resolved_text
        ctx.log_event(f"description → {_truncate(resolved_text)!r} (index {index})")
    else:
        await _send_error(ch, FDLogicError("`$description` requires 1-2 arguments: $description[text;index (optional)]"))