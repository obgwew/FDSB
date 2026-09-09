# cmds_FDScripts/editMessage.py
import discord
from FDScript import ExecutionContext, Command
from FDCore import FDSyntaxError, FDLogicError, _send_error, _parse_color

_EMBED_DEFAULT_COLOR = 0x2B2D31

async def _resolve_channel(ctx: ExecutionContext, channel_id: int) -> discord.abc.Messageable | None:
    channel = ctx.bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await ctx.bot.fetch_channel(channel_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$editMessage` requires at least 3 arguments: "
            "`$editMessage[channelID; messageID; content; (title; description; color; footer)]`"
        ))
        return

    channel_id_raw = ctx.resolve(args[0]).strip()
    message_id_raw = ctx.resolve(args[1]).strip()
    content        = ctx.resolve(args[2])

    title       = ctx.resolve(args[3]).strip() if len(args) > 3 else ""
    description = ctx.resolve(args[4]).strip() if len(args) > 4 else ""
    color_raw   = ctx.resolve(args[5]).strip() if len(args) > 5 else ""
    footer      = ctx.resolve(args[6]).strip() if len(args) > 6 else ""

    if not channel_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — the channel ID (1st arg) must be a valid snowflake (numbers only). Got: `{channel_id_raw}`"
        ))
        return

    if not message_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — the message ID (2nd arg) must be a valid snowflake (numbers only). Got: `{message_id_raw}`"
        ))
        return

    target_channel = await _resolve_channel(ctx, int(channel_id_raw))
    if target_channel is None:
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — no channel found with ID `{channel_id_raw}`"
        ))
        return

    try:
        target_message = await target_channel.fetch_message(int(message_id_raw))
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — no message found with ID `{message_id_raw}` in that channel"
        ))
        return
    except discord.Forbidden:
        await _send_error(ch, FDLogicError(
            "`$editMessage` — the bot doesn't have permission to view/fetch messages in that channel"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — failed to fetch message `{message_id_raw}`: `{e}`"
        ))
        return

    if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
        await _send_error(ch, FDLogicError(
            "`$editMessage` — the message ID (2nd arg) must point to a message sent by this bot"
        ))
        return

    kwargs: dict = {"content": content}

    if title or description or color_raw or footer:
        embed = discord.Embed(
            title=title,
            description=description,
            color=_parse_color(color_raw) if color_raw else _EMBED_DEFAULT_COLOR,
        )
        if footer:
            embed.set_footer(text=footer)
        kwargs["embed"] = embed

    try:
        await target_message.edit(**kwargs)
    except discord.Forbidden:
        await _send_error(ch, FDLogicError(
            "`$editMessage` — the bot doesn't have permission to edit that message"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$editMessage` — failed to edit message `{message_id_raw}`: `{e}`"
        ))
        return

    ctx.log_event(
        f"$editMessage → edited message {message_id_raw} in channel {channel_id_raw}"
        + (" (with embed)" if "embed" in kwargs else "")
    )