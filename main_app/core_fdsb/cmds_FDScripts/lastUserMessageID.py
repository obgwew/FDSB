# cmds_FDScripts/lastUserMessageID.py
import discord
from FDScript import ExecutionContext


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    msg = getattr(ctx, "message", None)
    if msg is not None:
        return str(msg.id)

    interaction = getattr(ctx, "interaction", None)
    if interaction is not None and interaction.message is not None:
        return str(interaction.message.id)

    return ""