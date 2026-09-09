# cmds_FDScripts/editButton.py
import discord
from FDScript import ExecutionContext, Command
from FDCore import BUTTON_STYLES, FDSyntaxError, FDLogicError, _send_error


def _find_button(view: discord.ui.View, target_id: str):
    for item in view.children:
        if isinstance(item, discord.ui.Button) and (item.custom_id == target_id or item.url == target_id):
            return item
    return None


def _apply(btn: discord.ui.Button, label: str, style: discord.ButtonStyle, disabled: bool, emoji: str | None):
    if not (label and label.strip()) and not emoji:
        label = "\u200b"
    else:
        label = label or None

    btn.label = label
    btn.disabled = disabled
    btn.emoji = emoji
    if btn.style != discord.ButtonStyle.link:
        btn.style = style


def _view_from_message(message: discord.Message, *, timeout=None) -> discord.ui.View:
    """يعيد بناء الـ View مع الحفاظ على رقم الصف (line) الأصلي"""
    view = discord.ui.View(timeout=timeout)
    for row_idx, action_row in enumerate(message.components):
        for component in action_row.children:
            item = discord.ui.Button.from_component(component)
            item.row = row_idx
            view.add_item(item)
    return view


def _sync_ctx_message(ctx: ExecutionContext, updated_message: discord.Message) -> None:
    if ctx.last_bot_message is not None and ctx.last_bot_message.id == updated_message.id:
        ctx.last_bot_message = updated_message
    if (
        ctx.interaction is not None
        and ctx.interaction.message is not None
        and ctx.interaction.message.id == updated_message.id
    ):
        ctx.interaction.message = updated_message


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable,
                  *, do_edit: bool = True) -> None:
    """
    do_edit=False → يطبّق التعديل على الـ View فقط بدون إرسال إلى ديسكورد
    (يُستخدم أثناء تجميع عدة $editButton متتالية)
    """
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$editButton` requires at least 3 arguments: "
            "`$editButton[ID/URL; label; style; (disabled; emoji; messageID)]`"
        ))
        return

    target_id = ctx.resolve(args[0]).strip()
    label = ctx.resolve(args[1])
    style_str = ctx.resolve(args[2]).strip().lower()
    disabled = len(args) > 3 and ctx.resolve(args[3]).strip().lower() == "yes"
    emoji = ctx.resolve(args[4]).strip() if len(args) > 4 and args[4].strip() else None
    message_id_arg = ctx.resolve(args[5]).strip() if len(args) > 5 and args[5].strip() else None

    if not target_id:
        await _send_error(ch, FDLogicError("`$editButton` — the ID/URL argument (1st arg) cannot be empty"))
        return

    if style_str not in BUTTON_STYLES:
        await _send_error(ch, FDLogicError(
            f"`$editButton` — unknown style `{style_str}`. "
            f"Valid styles: primary, secondary, success, danger, link"
        ))
        return

    style = BUTTON_STYLES[style_str]

    # ── messageID ────────────────────────────────────────
    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$editButton` — the message ID (6th arg) must be a valid snowflake (numbers only)"
            ))
            return

        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$editButton` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$editButton` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return

        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$editButton` — the message ID (6th arg) must point to a message sent by this bot"
            ))
            return

        if (getattr(ctx, '_edit_view_msg_id', None) == target_message.id
                and getattr(ctx, '_edit_view', None) is not None):
            view = ctx._edit_view
        else:
            view = _view_from_message(target_message, timeout=None)
            ctx._edit_view = view
            ctx._edit_view_msg_id = target_message.id
            ctx._edit_view_target = target_message

        btn = _find_button(view, target_id)
        if btn is None:
            await _send_error(ch, FDLogicError(
                f"`$editButton` — no button with ID `{target_id}` found on that message"
            ))
            return

        _apply(btn, label, style, disabled, emoji)

        if do_edit:
            try:
                updated_message = await target_message.edit(view=view)
            except discord.HTTPException as e:
                await _send_error(ch, FDLogicError(
                    f"`$editButton` — failed to edit message `{message_id_arg}`: `{e}`"
                ))
                return
            _sync_ctx_message(ctx, updated_message)

            ctx._edit_view = None
            ctx._edit_view_msg_id = None
            ctx._edit_view_target = None

        ctx.log_event(f"$editButton → edited [{target_id}] on message {message_id_arg}"
                      + ("" if do_edit else " (batched)"))
        return

    if ctx.view is not None:
        btn = _find_button(ctx.view, target_id)
        if btn is not None:
            _apply(btn, label, style, disabled, emoji)
            ctx.log_event(f"$editButton → edited [{target_id}] in pending view")
            return

    if ctx.interaction is not None and ctx.interaction.message is not None:
        source_message = ctx.interaction.message

        if (getattr(ctx, '_edit_view_msg_id', None) == source_message.id
                and getattr(ctx, '_edit_view', None) is not None):
            view = ctx._edit_view
        else:
            view = _view_from_message(source_message, timeout=None)
            ctx._edit_view = view
            ctx._edit_view_msg_id = source_message.id
            ctx._edit_view_target = source_message

        btn = _find_button(view, target_id)
        if btn is None:
            await _send_error(ch, FDLogicError(f"`$editButton` — no button with ID `{target_id}` found"))
            return

        _apply(btn, label, style, disabled, emoji)

        if do_edit:
            try:
                updated_message = await source_message.edit(view=view)
            except discord.HTTPException as e:
                await _send_error(ch, FDLogicError(f"`$editButton` — failed to edit the source message: `{e}`"))
                return
            ctx.interaction.message = updated_message
            _sync_ctx_message(ctx, updated_message)
            ctx._edit_view = None
            ctx._edit_view_msg_id = None
            ctx._edit_view_target = None

        ctx.log_event(f"$editButton → edited [{target_id}] on interaction source message"
                      + ("" if do_edit else " (batched)"))
        return

    if ctx.last_bot_message is not None:
        target_message = ctx.last_bot_message

        if (getattr(ctx, '_edit_view_msg_id', None) == target_message.id
                and getattr(ctx, '_edit_view', None) is not None):
            view = ctx._edit_view
        else:
            view = _view_from_message(target_message, timeout=None)
            ctx._edit_view = view
            ctx._edit_view_msg_id = target_message.id
            ctx._edit_view_target = target_message

        btn = _find_button(view, target_id)
        if btn is not None:
            _apply(btn, label, style, disabled, emoji)

            if do_edit:
                try:
                    updated_message = await target_message.edit(view=view)
                except discord.HTTPException as e:
                    await _send_error(ch, FDLogicError(
                        f"`$editButton` — failed to edit the last sent message: `{e}`"
                    ))
                    return
                ctx.last_bot_message = updated_message
                _sync_ctx_message(ctx, updated_message)
                ctx._edit_view = None
                ctx._edit_view_msg_id = None
                ctx._edit_view_target = None

            ctx.log_event(f"$editButton → edited [{target_id}] on last sent message ({target_message.id})"
                          + ("" if do_edit else " (batched)"))
            return

    await _send_error(ch, FDLogicError(
        f"`$editButton` — no button with ID `{target_id}` found "
        f"(nothing queued yet, and no messageID / interaction context to look in)"
    ))