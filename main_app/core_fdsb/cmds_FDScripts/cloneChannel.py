# cmds_FDScripts/cloneChannel.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
)

_CHANNEL_MENTION_RE = re.compile(r'^<#(\d+)>$')

_CLONEABLE_TYPES = (
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.StageChannel,
    discord.ForumChannel,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


def _resolve_channel_id(raw: str) -> int | None:
    raw = raw.strip()
    match = _CHANNEL_MENTION_RE.match(raw)
    if match:
        return int(match.group(1))
    if raw.isdigit():
        return int(raw)
    return None


def _find_channel(channel_id: int, ctx: ExecutionContext):
    channel = ctx.bot.get_channel(channel_id)
    if not channel and getattr(ctx.message, "guild", None):
        channel = ctx.message.guild.get_channel(channel_id)
    return channel


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDSyntaxError(
            "`$cloneChannel` requires at least 1 argument: "
            "`$cloneChannel[channel id to clone; new name (optional)]`"
        ))
        return

    channel_id_str = ctx.resolve(args[0]).strip()
    new_name = ctx.resolve(args[1]).strip() if len(args) > 1 and args[1].strip() else None

    channel_id = _resolve_channel_id(channel_id_str)
    if channel_id is None:
        await _send_error(ch, FDLogicError(
            f"`$cloneChannel` — invalid channel reference `{channel_id_str}` "
            f"(expected a channel mention or a numeric ID)"
        ))
        return

    source_channel = _find_channel(channel_id, ctx)
    if source_channel is None:
        await _send_error(ch, FDLogicError(
            f"`$cloneChannel` — no channel found with ID `{channel_id}`"
        ))
        return

    if not getattr(source_channel, "guild", None):
        await _send_error(ch, FDLogicError(
            "`$cloneChannel` — that channel isn't part of a guild and can't be cloned"
        ))
        return

    if not isinstance(source_channel, _CLONEABLE_TYPES):
        await _send_error(ch, FDLogicError(
            f"`$cloneChannel` — channel type `{source_channel.type.name}` cannot be cloned"
        ))
        return

    try:
        cloned_channel = await source_channel.clone(
            name=new_name,
            reason=f"Cloned via $cloneChannel by {ctx.message.author} ({ctx.message.author.id})",
        )
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$cloneChannel` — bot lacks `Manage Channels` permission to clone that channel"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDEnvironmentError(
            f"`$cloneChannel` — failed to clone channel: HTTP {e.status}: {e.text}"
        ))
        return
    except Exception as ex:
        await _send_error(ch, FDLogicError(f"`$cloneChannel` — unexpected error: {ex}"))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(f"<#{cloned_channel.id}>")
    ctx.last_bot_message = sent

    ctx.log_event(
        f"cloneChannel → cloned `{_truncate(source_channel.name)}` "
        f"({source_channel.id}) → `{_truncate(cloned_channel.name)}` ({cloned_channel.id})"
    )