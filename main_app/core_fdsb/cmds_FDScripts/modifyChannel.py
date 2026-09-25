# cmds_FDScripts/modifyChannel.py
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
    if len(args) < 1 or not args[0].strip():
        await _send_error(ch, FDSyntaxError(
            "`$modifyChannel` — requires at least the Channel ID: `$modifyChannel[Channel ID;(Channel Name;Topic;Make NSFW?;Position;Category ID)]`"
        ))
        return

    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$modifyChannel` — can only be used inside a server, not in DMs."
        ))
        return

    channel_raw = ctx.resolve(args[0]).strip()
    clean_id_str = re.sub(r"\D", "", channel_raw)

    if not clean_id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$modifyChannel` — channel ID or mention must be a numeric snowflake (got `{channel_raw}`)"
        ))
        return

    channel_id = int(clean_id_str)
    channel = guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await ctx.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            channel = None

    if channel is None:
        await _send_error(ch, FDLogicError(
            f"`$modifyChannel` — no channel found with ID `{channel_id}`"
        ))
        return

    if getattr(channel, "guild", None) is None or channel.guild.id != guild.id:
        await _send_error(ch, FDLogicError(
            f"`$modifyChannel` — channel `{channel.id}` does not belong to this server"
        ))
        return

    if not hasattr(channel, "edit"):
        await _send_error(ch, FDLogicError(
            f"`$modifyChannel` — channel `{channel.name}` does not support modifications"
        ))
        return

    edit_kwargs = {}

    if len(args) > 1 and args[1].strip():
        new_name = ctx.resolve(args[1]).strip()
        if not (1 <= len(new_name) <= 100):
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — channel name must be between 1 and 100 characters (got `{len(new_name)}`)"
            ))
            return
        edit_kwargs["name"] = new_name

    if len(args) > 2 and args[2].strip():
        new_topic = ctx.resolve(args[2])
        if not hasattr(channel, "topic"):
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — channel `{channel.name}` does not support topics"
            ))
            return
        if len(new_topic) > 1024:
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — topic exceeds maximum length of 1024 characters (got `{len(new_topic)}`)"
            ))
            return
        edit_kwargs["topic"] = None if new_topic.strip().lower() == "none" else new_topic

    if len(args) > 3 and args[3].strip():
        nsfw_raw = ctx.resolve(args[3]).strip().lower()
        if nsfw_raw not in ("yes", "no", "true", "false"):
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — invalid NSFW value `{nsfw_raw}` (expected 'yes' or 'no')"
            ))
            return
        if not hasattr(channel, "nsfw"):
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — channel `{channel.name}` does not support NSFW setting"
            ))
            return
        edit_kwargs["nsfw"] = nsfw_raw in ("yes", "true")

    if len(args) > 4 and args[4].strip():
        pos_raw = ctx.resolve(args[4]).strip()
        if not pos_raw.isdigit():
            await _send_error(ch, FDLogicError(
                f"`$modifyChannel` — position must be a positive integer (got `{pos_raw}`)"
            ))
            return
        edit_kwargs["position"] = int(pos_raw)

    if len(args) > 5 and args[5].strip():
        cat_raw = ctx.resolve(args[5]).strip()
        if isinstance(channel, discord.CategoryChannel):
            await _send_error(ch, FDLogicError(
                "`$modifyChannel` — cannot assign a category to another category"
            ))
            return

        if cat_raw.lower() in ("none", "0", "null"):
            edit_kwargs["category"] = None
        else:
            clean_cat_id = re.sub(r"\D", "", cat_raw)
            if not clean_cat_id.isdigit():
                await _send_error(ch, FDLogicError(
                    f"`$modifyChannel` — category ID must be a numeric snowflake (got `{cat_raw}`)"
                ))
                return

            cat_id = int(clean_cat_id)
            category = guild.get_channel(cat_id)

            if category is None:
                try:
                    category = await ctx.bot.fetch_channel(cat_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    category = None

            if category is None or not isinstance(category, discord.CategoryChannel):
                await _send_error(ch, FDLogicError(
                    f"`$modifyChannel` — no category found with ID `{cat_id}` in this server"
                ))
                return

            if category.guild.id != guild.id:
                await _send_error(ch, FDLogicError(
                    f"`$modifyChannel` — category `{cat_id}` does not belong to this server"
                ))
                return

            edit_kwargs["category"] = category

    if not edit_kwargs:
        await _send_error(ch, FDLogicError(
            "`$modifyChannel` — no modification parameters were provided"
        ))
        return

    edit_reason = f"Channel modified via $modifyChannel by {ctx.message.author}"
    try:
        await channel.edit(**edit_kwargs, reason=edit_reason)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$modifyChannel` — bot lacks `Manage Channels` permission to modify this channel"
        ))
        return
    except discord.HTTPException as e:
        if getattr(e, "status", None) == 429:
            retry_after = getattr(e, "retry_after", 1)
            await asyncio.sleep(retry_after)
            try:
                await channel.edit(**edit_kwargs, reason=edit_reason)
            except discord.HTTPException as e2:
                await _send_error(ch, FDRuntimeError(
                    f"`$modifyChannel` — failed to modify channel after retry: `{e2.text}`"
                ))
                return
        else:
            await _send_error(ch, FDRuntimeError(
                f"`$modifyChannel` — failed to modify channel: `{e.text}`"
            ))
            return

    ctx.log_event(
        f"modifyChannel → modified channel `{channel.id}` ({channel.name}) with parameters: {list(edit_kwargs.keys())}"
    )