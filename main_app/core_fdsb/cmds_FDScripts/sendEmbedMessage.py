# cmds_FDScripts/sendEmbedMessage.py
from datetime import datetime, timezone

import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _parse_color, _truncate,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


def _arg(args: list[str], index: int, ctx: ExecutionContext) -> str:
    return ctx.resolve(args[index]).strip() if index < len(args) else ""


def _is_yes(raw: str) -> bool:
    return raw.strip().lower() == "yes"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 1 or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$sendEmbedMessage` requires at least the channel ID:\n"
            "`$sendEmbedMessage[Channel ID;Content;(Title;Title URL;Description;Color hex;"
            "Author;Author icon;Footer;Footer icon;Thumbnail;Image;Add timestamp?;Return ID?)]`"
        ))
        return

    ch_id_str = ctx.resolve(args[0]).strip()
    try:
        ch_id = int(ch_id_str)
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$sendEmbedMessage` — invalid channel ID: `{ch_id_str}`"
        ))
        return

    target_ch = ctx.bot.get_channel(ch_id)
    if not target_ch:
        await _send_error(ch, FDEnvironmentError(
            f"`$sendEmbedMessage` — channel `{ch_id_str}` not found or bot has no access"
        ))
        return

    content       = ctx.resolve(args[1]) if len(args) > 1 else ""
    title         = _arg(args, 2, ctx)
    title_url     = _arg(args, 3, ctx)
    description   = _arg(args, 4, ctx)
    color_hex     = _arg(args, 5, ctx)
    author        = _arg(args, 6, ctx)
    author_icon   = _arg(args, 7, ctx)
    footer        = _arg(args, 8, ctx)
    footer_icon   = _arg(args, 9, ctx)
    thumbnail     = _arg(args, 10, ctx)
    image         = _arg(args, 11, ctx)
    add_timestamp = _arg(args, 12, ctx)
    return_id     = _arg(args, 13, ctx)

    embed = discord.Embed(color=_parse_color(color_hex))
    if title:
        embed.title = title
    if title_url:
        embed.url = title_url
    if description:
        embed.description = description
    if author or author_icon:
        embed.set_author(name=author or "\u200b", icon_url=author_icon or None)
    if footer or footer_icon:
        embed.set_footer(text=footer or "\u200b", icon_url=footer_icon or None)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    if _is_yes(add_timestamp):
        embed.timestamp = datetime.now(timezone.utc)

    try:
        ctx.stop_typing()
        sent = await target_ch.send(content=content or None, embed=embed)
        ctx.last_bot_message = sent

        if _is_yes(return_id):
            id_content = f"{content}\n{sent.id}" if content else str(sent.id)
            try:
                await sent.edit(content=id_content)
            except discord.HTTPException:
                pass

        log_label = title or content
        ctx.log_event(f"sendEmbedMessage [{_truncate(log_label)}] → sent to channel {ch_id_str}")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$sendEmbedMessage` — bot lacks permission to send in channel `{ch_id_str}`"
        ))
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$sendEmbedMessage` — failed to send: `{e.text}`"
        ))