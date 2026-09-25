# cmds_FDScripts/editChannelTopic.py
import asyncio
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 1:
        await _send_error(ch, FDSyntaxError(
            "`$editChannelTopic` — requires at least 1 argument: `$editChannelTopic[(channel ID); new topic]`"
        ))
        return

    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$editChannelTopic` — can only be used inside a server, not in DMs."
        ))
        return

    target_channel = None
    new_topic = ""

    if len(args) == 1:
        target_channel = ctx.message.channel
        new_topic = ctx.resolve(args[0])
    else:
        channel_raw = ctx.resolve(args[0]).strip()
        new_topic = ctx.resolve(args[1])

        if not channel_raw:
            target_channel = ctx.message.channel
        else:
            clean_id_str = re.sub(r"\D", "", channel_raw)
            if not clean_id_str.isdigit():
                await _send_error(ch, FDLogicError(
                    f"`$editChannelTopic` — channel ID or mention must be a numeric snowflake (got `{channel_raw}`)"
                ))
                return

            channel_id = int(clean_id_str)
            target_channel = guild.get_channel(channel_id)

            if target_channel is None:
                try:
                    target_channel = await ctx.bot.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    target_channel = None

            if target_channel is None:
                await _send_error(ch, FDLogicError(
                    f"`$editChannelTopic` — no channel found with ID `{channel_id}`"
                ))
                return

    if getattr(target_channel, "guild", None) is None or target_channel.guild.id != guild.id:
        await _send_error(ch, FDLogicError(
            f"`$editChannelTopic` — channel `{target_channel.id}` does not belong to this server"
        ))
        return

    if not hasattr(target_channel, "topic") or not hasattr(target_channel, "edit"):
        await _send_error(ch, FDLogicError(
            f"`$editChannelTopic` — channel `{target_channel.name}` does not support topics"
        ))
        return

    if len(new_topic) > 1024:
        await _send_error(ch, FDLogicError(
            f"`$editChannelTopic` — topic exceeds Discord maximum length of 1024 characters (got `{len(new_topic)}`)"
        ))
        return

    formatted_topic = new_topic if new_topic.strip() else None

    if getattr(target_channel, "topic", None) == formatted_topic:
        ctx.log_event(
            f"editChannelTopic → channel `{target_channel.id}` ({target_channel.name}) topic is already up to date, no-op"
        )
        return

    edit_reason = f"Topic edited via $editChannelTopic by {ctx.message.author}"
    try:
        await target_channel.edit(topic=formatted_topic, reason=edit_reason)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editChannelTopic` — bot lacks `Manage Channels` permission to edit this channel topic"
        ))
        return
    except discord.HTTPException as e:
        if getattr(e, "status", None) == 429:
            retry_after = getattr(e, "retry_after", 1)
            await asyncio.sleep(retry_after)
            try:
                await target_channel.edit(topic=formatted_topic, reason=edit_reason)
            except discord.HTTPException as e2:
                await _send_error(ch, FDRuntimeError(
                    f"`$editChannelTopic` — failed to edit channel topic after retry: `{e2.text}`"
                ))
                return
        else:
            await _send_error(ch, FDRuntimeError(
                f"`$editChannelTopic` — failed to edit channel topic: `{e.text}`"
            ))
            return

    ctx.log_event(
        f"editChannelTopic → updated topic for channel `{target_channel.id}` ({target_channel.name})"
    )