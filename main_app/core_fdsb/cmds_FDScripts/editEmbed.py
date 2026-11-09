# cmds_FDScripts/editEmbed.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)
from engine_FDScript.parse_utils import _try_parse_color, _NAMED_COLORS
from engine_FDScript.embed_ops import build_edited_embeds, edit_target_channel

_USAGE = "`$editEmbed[messageID;(title);(description);(footer);(color)]`"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not 2 <= len(args) <= 5:
        await _send_error(ch, FDSyntaxError(
            f"`$editEmbed` — expected 2 to 5 arguments: {_USAGE} (got {len(args)})"
        ))
        return

    vals = [ctx.resolve(a).strip() for a in args]
    msg_id_raw, title, description, footer, color_raw = (vals + [""] * 5)[:5]

    if not msg_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editEmbed` — message ID must be a numeric snowflake (got `{msg_id_raw}`)"
        ))
        return

    if not (title or description or footer or color_raw):
        await _send_error(ch, FDSyntaxError(
            "`$editEmbed` — nothing to change: give at least one of title, description, footer, color"
        ))
        return

    color = None
    if color_raw:
        color = _try_parse_color(color_raw)
        if color is None:
            await _send_error(ch, FDLogicError(
                f"`$editEmbed` — invalid color `{color_raw}` (use a hex value like `#ff0000` or a color name)\n"
                f"Named colors: {', '.join(sorted(_NAMED_COLORS))}"
            ))
            return

    channel = edit_target_channel(ctx)
    if channel is None:
        await _send_error(ch, FDEnvironmentError(
            "`$editEmbed` — no channel available in this context to look the message up in"
        ))
        return

    try:
        message = await channel.fetch_message(int(msg_id_raw))
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$editEmbed` — message `{msg_id_raw}` was not found in this channel"
        ))
        return
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editEmbed` — the bot cannot read that channel's message history"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDEnvironmentError(f"`$editEmbed` — Discord error while fetching the message: {e.text}"))
        return

    embeds = build_edited_embeds(
        message,
        title=title or None,
        description=description or None,
        footer=footer or None,
        color=color,
    )
    if embeds is None:
        await _send_error(ch, FDLogicError(
            f"`$editEmbed` — message `{msg_id_raw}` has no embed to edit"
        ))
        return

    try:
        edited = await message.edit(embeds=embeds)
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editEmbed` — the bot cannot edit that message (only messages sent by the bot can be edited)"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(f"`$editEmbed` — Discord rejected the edit: {e.text}"))
        return

    last = ctx.last_bot_message
    if edited is not None and last is not None and last.id == message.id:
        ctx.last_bot_message = edited

    changed = [n for n, v in (("title", title), ("description", description),
                              ("footer", footer), ("color", color_raw)) if v]
    ctx.log_event(f"editEmbed → message {message.id} embed updated ({', '.join(changed)})")