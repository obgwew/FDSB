# cmds_FDScripts/dm.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error, _resolve_dm_target,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        ctx.dm_target = ctx.message.author
    else:
        ctx.dm_target = ctx.resolve(args[0]).strip() or ctx.message.author
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        ctx.dm_target = ctx.message.author
        ctx.log_event(f"dm → target set to author ({ctx.message.author.id})")
        return

    target_str = ctx.resolve(args[0]).strip()
    if not target_str:
        await _send_error(ch, FDLogicError(
            "`$dm[]` — target cannot be empty. "
            "Use `$dm` (no brackets) to DM the command author."
        ))
        return

    target_user = await _resolve_dm_target(target_str, ctx, ch)
    if target_user is None:
        return

    ctx.dm_target = target_user
    ctx.log_event(f"dm → target set to {target_user} ({target_user.id})")