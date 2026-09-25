# cmds_FDScripts/moveChannel.py
import asyncio
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDSyntaxError(
            "`$moveChannel` — requires 2 arguments: `$moveChannel[channel ID; new category ID]`"
        ))
        return

    channel_id_raw = ctx.resolve(args[0]).strip()
    category_id_raw = ctx.resolve(args[1]).strip()

    if not channel_id_raw:
        await _send_error(ch, FDLogicError(
            "`$moveChannel` — the channel ID argument cannot be empty"
        ))
        return

    if not category_id_raw:
        await _send_error(ch, FDLogicError(
            "`$moveChannel` — the new category ID argument cannot be empty"
        ))
        return

    if not channel_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — channel ID must be a numeric snowflake (got `{channel_id_raw}`)"
        ))
        return

    if not category_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — new category ID must be a numeric snowflake (got `{category_id_raw}`)"
        ))
        return

    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$moveChannel` — no guild available in this context (cannot be used in DMs)"
        ))
        return

    channel_id = int(channel_id_raw)
    category_id = int(category_id_raw)

    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await ctx.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            channel = None

    if channel is None or not isinstance(channel, (discord.abc.GuildChannel,)):
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — no channel found with ID `{channel_id}` in this guild"
        ))
        return

    if getattr(channel, "guild", None) is None or channel.guild.id != guild.id:
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — channel `{channel_id}` does not belong to this guild"
        ))
        return

    category = guild.get_channel(category_id)
    if category is None:
        try:
            category = await ctx.bot.fetch_channel(category_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            category = None

    if category is None or not isinstance(category, discord.CategoryChannel):
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — no category found with ID `{category_id}` in this guild"
        ))
        return

    if category.guild.id != guild.id:
        await _send_error(ch, FDLogicError(
            f"`$moveChannel` — category `{category_id}` does not belong to this guild"
        ))
        return

    if isinstance(channel, discord.CategoryChannel):
        await _send_error(ch, FDLogicError(
            "`$moveChannel` — the target of `$moveChannel` must be a regular channel, "
            "not another category"
        ))
        return

    if getattr(channel, "category_id", None) == category.id:
        ctx.log_event(
            f"moveChannel → channel `{channel.id}` is already in category `{category.id}`, no-op"
        )
        return

    try:
        await channel.edit(category=category, reason=f"Moved via $moveChannel by {ctx.message.author}")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$moveChannel` — bot lacks `Manage Channels` permission to move this channel"
        ))
        return
    except discord.HTTPException as e:
        if getattr(e, "status", None) == 429:
            retry_after = getattr(e, "retry_after", 1)
            await asyncio.sleep(retry_after)
            try:
                await channel.edit(category=category, reason=f"Moved via $moveChannel by {ctx.message.author}")
            except discord.HTTPException as e2:
                await _send_error(ch, FDRuntimeError(
                    f"`$moveChannel` — failed to move channel after retry: `{e2.text}`"
                ))
                return
        else:
            await _send_error(ch, FDRuntimeError(
                f"`$moveChannel` — failed to move channel: `{e.text}`"
            ))
            return

    ctx.log_event(
        f"moveChannel → moved channel `{channel.id}` ({channel.name}) to category "
        f"`{category.id}` ({category.name})"
    )