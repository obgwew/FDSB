# cmds_FDScripts/color.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, _send_error, _parse_color, _NAMED_COLORS,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        index = 1
        if len(args) > 1:
            idx_str = ctx.resolve(args[1]).strip()
            if idx_str.isdigit():
                index = int(idx_str)
        ctx.get_embed_builder(index).color = _parse_color(ctx.resolve(args[0]).strip())
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) in (1, 2):
        index = 1
        if len(args) == 2:
            idx_str = ctx.resolve(args[1]).strip()
            if not idx_str.isdigit():
                await _send_error(ch, FDLogicError("`$color` index must be a number: $color[hex or name;index]"))
                return
            index = int(idx_str)
        resolved_color = ctx.resolve(args[0]).strip()
        if not resolved_color:
            await _send_error(ch, FDLogicError("`$color` requires a non-empty color value."))
            return
        ctx.get_embed_builder(index).color = _parse_color(resolved_color)
        ctx.log_event(f"color → {resolved_color!r} (index {index})")
    else:
        await _send_error(ch, FDLogicError(
            "`$color` requires 1-2 arguments: $color[hex or name;index (optional)]\n"
            f"Named colors: {', '.join(sorted(_NAMED_COLORS))}"
        ))