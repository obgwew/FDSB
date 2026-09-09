# cmds_FDScripts/addButton.py
from typing import Optional

import discord

from FDScript import ExecutionContext, Command
from FDCore import BUTTON_STYLES, FDSyntaxError, FDLogicError, _send_error

MAX_BUTTONS_PER_MESSAGE = 25
MAX_BUTTONS_PER_ROW = 5
MAX_ROWS = 5

def _build_button(is_link: bool, url_or_id: str, label: str, style: discord.ButtonStyle,
                   disabled: bool, emoji: str | None, row: int) -> discord.ui.Button:
    if is_link:
        return discord.ui.Button(label=label, url=url_or_id, disabled=disabled, emoji=emoji, row=row)
    return discord.ui.Button(custom_id=url_or_id, label=label, style=style, disabled=disabled, emoji=emoji, row=row)

def _has_duplicate_id(view: discord.ui.View, custom_id: str) -> bool:
    return any(
        isinstance(item, discord.ui.Button) and item.custom_id == custom_id
        for item in view.children
    )

def _next_row(view: discord.ui.View, new_line: bool) -> Optional[int]:
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    if not buttons:
        return 0

    row_counts: dict[int, int] = {}
    for b in buttons:
        r = b.row if b.row is not None else 0
        row_counts[r] = row_counts.get(r, 0) + 1

    last_row = max(row_counts)

    if not new_line:
        if row_counts.get(last_row, 0) < MAX_BUTTONS_PER_ROW:
            return last_row
        new_line = True

    if new_line:
        next_row = last_row + 1
        if next_row >= MAX_ROWS:
            return None
        return next_row

    return None

async def _edit_target_with_button(ch: discord.abc.Messageable, ctx: ExecutionContext,
                                    target_message: discord.Message, btn: discord.ui.Button,
                                    is_link: bool, url_or_id: str) -> bool:
    existing_view = discord.ui.View.from_message(target_message, timeout=None)

    if len(existing_view.children) >= MAX_BUTTONS_PER_MESSAGE:
        await _send_error(ch, FDLogicError(
            f"`$addButton` — that message already has {MAX_BUTTONS_PER_MESSAGE} buttons"
        ))
        return False

    if not is_link and _has_duplicate_id(existing_view, url_or_id):
        await _send_error(ch, FDLogicError(
            f"`$addButton` — duplicate custom_id `{url_or_id}` on that message"
        ))
        return False

    existing_view.add_item(btn)
    try:
        updated_message = await target_message.edit(view=existing_view)
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$addButton` — failed to edit message `{target_message.id}`: `{e}`"
        ))
        return False

    if ctx.last_bot_message is not None and ctx.last_bot_message.id == updated_message.id:
        ctx.last_bot_message = updated_message
    if (
        ctx.interaction is not None
        and ctx.interaction.message is not None
        and ctx.interaction.message.id == updated_message.id
    ):
        ctx.interaction.message = updated_message

    return True

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 4:
        await _send_error(ch, FDSyntaxError(
            "`$addButton` requires at least 4 arguments: "
            "`$addButton[newLine; ID/URL; label; style; (disabled; emoji; messageID)]`"
        ))
        return

    new_line = ctx.resolve(args[0]).strip().lower() == "yes"
    url_or_id = ctx.resolve(args[1]).strip()
    label = ctx.resolve(args[2])
    style_str = ctx.resolve(args[3]).strip().lower()
    disabled = len(args) > 4 and ctx.resolve(args[4]).strip().lower() == "yes"
    emoji = ctx.resolve(args[5]).strip() if len(args) > 5 and args[5].strip() else None
    message_id_arg = ctx.resolve(args[6]).strip() if len(args) > 6 and args[6].strip() else None

    if not label.strip() and not emoji:
        label = "\u200b"
        _log_label = f"{url_or_id} (blank label)"
    else:
        _log_label = label or url_or_id

    if style_str not in BUTTON_STYLES:
        await _send_error(ch, FDLogicError(
            f"`$addButton` — unknown style `{style_str}`. "
            f"Valid styles: primary, secondary, success, danger, link"
        ))
        return

    is_link = style_str == "link"

    if not url_or_id:
        await _send_error(ch, FDLogicError(
            "`$addButton` — the ID/URL argument (2nd arg) cannot be empty"
        ))
        return

    if is_link and not (url_or_id.startswith("http://") or url_or_id.startswith("https://")):
        await _send_error(ch, FDLogicError(
            "`$addButton` — link buttons need a URL starting with http:// or https://"
        ))
        return

    style = BUTTON_STYLES[style_str]

    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$addButton` — the message ID (7th arg) must be a valid snowflake (numbers only)"
            ))
            return

        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$addButton` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$addButton` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return

        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$addButton` — the message ID (7th arg) must point to a message sent by this bot"
            ))
            return

        existing_view = discord.ui.View.from_message(target_message, timeout=None)
        row = _next_row(existing_view, new_line)
        if row is None:
            await _send_error(ch, FDLogicError(
                f"`$addButton` — that message has no room left "
                f"(max {MAX_ROWS} rows × {MAX_BUTTONS_PER_ROW} buttons)"
            ))
            return

        btn = _build_button(is_link, url_or_id, label, style, disabled, emoji, row)

        ok = await _edit_target_with_button(ch, ctx, target_message, btn, is_link, url_or_id)
        if not ok:
            return

        ctx.log_event(f"$addButton → attached [{_log_label}] to message {message_id_arg}")
        return

    if ctx.view is None:
        ctx.view = discord.ui.View(timeout=None)

    if len(ctx.view.children) >= MAX_BUTTONS_PER_MESSAGE:
        await _send_error(ch, FDLogicError(
            f"`$addButton` — a message can have at most {MAX_BUTTONS_PER_MESSAGE} buttons"
        ))
        return

    if not is_link and _has_duplicate_id(ctx.view, url_or_id):
        await _send_error(ch, FDLogicError(
            f"`$addButton` — duplicate custom_id `{url_or_id}` in the same message"
        ))
        return

    row = _next_row(ctx.view, new_line)
    if row is None:
        await _send_error(ch, FDLogicError(
            f"`$addButton` — no room left "
            f"(max {MAX_ROWS} rows × {MAX_BUTTONS_PER_ROW} buttons)"
        ))
        return

    btn = _build_button(is_link, url_or_id, label, style, disabled, emoji, row)

    ctx.view.add_item(btn)
    ctx.log_event(f"$addButton → queued [{_log_label}] style={style_str} id={url_or_id} row={row}")