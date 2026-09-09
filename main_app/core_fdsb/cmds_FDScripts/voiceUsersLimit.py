# cmds_FDScripts/voiceUsersLimit.py
import discord
from FDScript import (
    ExecutionContext,
    FDSyntaxError, FDLogicError, FDEnvironmentError
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    if len(args) != 1:
        ctx._abort_with_error(FDSyntaxError(
            "`$voiceUsersLimit` requires exactly 1 argument: `$voiceUsersLimit[VoiceChannelID]`"
        ))
        return None

    channel_id_raw = ctx.resolve(args[0]).strip()
    
    if not channel_id_raw.isdigit():
        ctx._abort_with_error(FDLogicError(
            f"`$voiceUsersLimit` — channel ID must be numeric, got `{channel_id_raw}`"
        ))
        return None

    channel_id = int(channel_id_raw)
    
    guild = getattr(ctx.message, 'guild', None)
    if guild is None:
        channel = ctx.bot.get_channel(channel_id)
    else:
        channel = guild.get_channel(channel_id)

    if channel is None:
        ctx._abort_with_error(FDEnvironmentError(
            f"`$voiceUsersLimit` — channel `{channel_id_raw}` not found (make sure the bot can see it)."
        ))
        return None

    if not hasattr(channel, 'user_limit'):
        ctx._abort_with_error(FDLogicError(
            f"`$voiceUsersLimit` — channel `{channel.name}` is not a Voice/Stage channel."
        ))
        return None

    return str(channel.user_limit)