# cmds_FDScripts/lastBotMessageID.py
import discord
from FDScript import ExecutionContext


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    last_msg = ctx.last_bot_message
    if last_msg is not None:
        return str(last_msg.id)

    edit_target = getattr(ctx, "_edit_view_target", None)
    if edit_target is not None:
        return str(edit_target.id)

    interaction = getattr(ctx, "interaction", None)
    if interaction is not None and interaction.message is not None:
        return str(interaction.message.id)

    return ""