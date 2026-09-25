# cmds_FDScripts/syncChannel.py
import asyncio
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, FDRuntimeError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$syncChannel` — can only be used inside a server, not in DMs."
        ))
        return

    target_channel = None

    if not args or not args[0].strip():
        target_channel = ctx.message.channel
    else:
        raw_channel = ctx.resolve(args[0]).strip()
        clean_id_str = re.sub(r"\D", "", raw_channel)

        if not clean_id_str.isdigit():
            await _send_error(ch, FDLogicError(
                f"`$syncChannel` — channel ID or mention must be a numeric snowflake (got `{raw_channel}`)"
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
                f"`$syncChannel` — no channel found with ID `{channel_id}`"
            ))
            return

    if getattr(target_channel, "guild", None) is None or target_channel.guild.id != guild.id:
        await _send_error(ch, FDLogicError(
            f"`$syncChannel` — channel `{target_channel.id}` does not belong to this server"
        ))
        return

    if isinstance(target_channel, discord.CategoryChannel):
        await _send_error(ch, FDLogicError(
            "`$syncChannel` — target must be a regular channel, not a category"
        ))
        return

    category = getattr(target_channel, "category", None)
    if category is None:
        await _send_error(ch, FDLogicError(
            f"`$syncChannel` — channel `{target_channel.name}` does not belong to any category to sync with"
        ))
        return

    if getattr(target_channel, "permissions_synced", False):
        ctx.log_event(
            f"syncChannel → channel `{target_channel.id}` ({target_channel.name}) permissions are already synced with category `{category.name}`, no-op"
        )
        return

    sync_reason = f"Permissions synced via $syncChannel by {ctx.message.author}"
    try:
        await target_channel.edit(sync_permissions=True, reason=sync_reason)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$syncChannel` — bot lacks permission (requires `Manage Channels` and `Manage Roles/Permissions`)"
        ))
        return
    except discord.HTTPException as e:
        if getattr(e, "status", None) == 429:
            retry_after = getattr(e, "retry_after", 1)
            await asyncio.sleep(retry_after)
            try:
                await target_channel.edit(sync_permissions=True, reason=sync_reason)
            except discord.HTTPException as e2:
                await _send_error(ch, FDRuntimeError(
                    f"`$syncChannel` — failed to sync permissions after retry: `{e2.text}`"
                ))
                return
        else:
            await _send_error(ch, FDRuntimeError(
                f"`$syncChannel` — failed to sync permissions: `{e.text}`"
            ))
            return

    ctx.log_event(
        f"syncChannel → synced permissions for channel `{target_channel.id}` ({target_channel.name}) with category `{category.id}` ({category.name})"
    )