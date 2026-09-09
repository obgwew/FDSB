# cmds_FDScripts/boostLevel.py
import discord
from FDScript import (
    ExecutionContext,
    FDEnvironmentError
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    guild = getattr(ctx.message, 'guild', None)
    
    if guild is None:
        ctx._abort_with_error(FDEnvironmentError(
            "`$boostLevel` can only be used inside a server."
        ))
        return None

    return str(guild.premium_tier)