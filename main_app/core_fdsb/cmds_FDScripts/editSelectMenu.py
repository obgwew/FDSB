# cmds_FDScripts/editSelectMenu.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError,
    _send_error,
)

MAX_SELECT_VALUES = 25


def _get_registry(ctx: ExecutionContext) -> dict:
    registry = getattr(ctx, "_select_menus", None)
    if registry is None:
        registry = {}
        setattr(ctx, "_select_menus", registry)
    return registry


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def _fetch_target_message(ch: discord.abc.Messageable, ctx: ExecutionContext,
                                 message_id_arg: str | None) -> discord.Message | None:
    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$editSelectMenu` — the message ID (5th arg) must be a valid snowflake (numbers only)"
            ))
            return None
        try:
            return await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$editSelectMenu` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return None
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$editSelectMenu` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return None

    if ctx.interaction is not None and ctx.interaction.message is not None:
        return ctx.interaction.message

    if ctx.last_bot_message is not None:
        return ctx.last_bot_message

    await _send_error(ch, FDLogicError(
        "`$editSelectMenu` — no target message: provide a message ID (5th arg), "
        "or use this command inside an interaction / after sending a message"
    ))
    return None


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$editSelectMenu` requires at least 3 arguments: "
            "`$editSelectMenu[Menu ID;Min;Max;(Placeholder;Message ID)]`"
        ))
        return

    menu_id = ctx.resolve(args[0]).strip()
    min_str = ctx.resolve(args[1]).strip()
    max_str = ctx.resolve(args[2]).strip()
    placeholder = ctx.resolve(args[3]) if len(args) > 3 and args[3].strip() else None
    message_id_arg = ctx.resolve(args[4]).strip() if len(args) > 4 and args[4].strip() else None

    if not menu_id:
        await _send_error(ch, FDLogicError("`$editSelectMenu` — the Menu ID (1st arg) cannot be empty"))
        return

    if not min_str.isdigit() or not max_str.isdigit():
        await _send_error(ch, FDLogicError(
            "`$editSelectMenu` — Min and Max (2nd/3rd args) must be numbers"
        ))
        return

    min_values = int(min_str)
    max_values = int(max_str)

    if not (0 <= min_values <= MAX_SELECT_VALUES):
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenu` — Min must be between 0 and {MAX_SELECT_VALUES}"
        ))
        return

    if not (1 <= max_values <= MAX_SELECT_VALUES):
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenu` — Max must be between 1 and {MAX_SELECT_VALUES}"
        ))
        return

    if min_values > max_values:
        await _send_error(ch, FDLogicError(
            "`$editSelectMenu` — Min cannot be greater than Max"
        ))
        return

    if ctx.bot.user is None:
        await _send_error(ch, FDLogicError("`$editSelectMenu` — bot user is unavailable"))
        return

    target_message = await _fetch_target_message(ch, ctx, message_id_arg)
    if target_message is None:
        return

    if target_message.author.id != ctx.bot.user.id:
        await _send_error(ch, FDLogicError(
            "`$editSelectMenu` — the target message must have been sent by this bot"
        ))
        return

    existing_view = discord.ui.View.from_message(target_message, timeout=None)

    old_select: discord.ui.Select | None = None
    other_items = []
    for item in existing_view.children:
        if isinstance(item, discord.ui.Select) and item.custom_id == menu_id:
            old_select = item
        else:
            other_items.append(item)

    if old_select is None:
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenu` — no select menu with ID `{menu_id}` was found on that message"
        ))
        return

    new_select = discord.ui.Select(
        custom_id=menu_id,
        placeholder=placeholder,
        min_values=min_values,
        max_values=max_values,
        options=old_select.options,
        row=old_select.row,
    )

    new_view = discord.ui.View(timeout=None)
    for item in other_items:
        new_view.add_item(item)
    new_view.add_item(new_select)

    try:
        updated_message = await target_message.edit(view=new_view)
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenu` — failed to update message `{target_message.id}`: `{e}`"
        ))
        return

    if ctx.last_bot_message is not None and ctx.last_bot_message.id == updated_message.id:
        ctx.last_bot_message = updated_message
    if (
        ctx.interaction is not None
        and ctx.interaction.message is not None
        and ctx.interaction.message.id == updated_message.id
    ):
        ctx.interaction.message = updated_message

    registry = _get_registry(ctx)
    registry[menu_id] = {
        "select": new_select,
        "message_id": updated_message.id,
        "added_to_view": True,
    }

    ctx.log_event(f"editSelectMenu → updated `{menu_id}` (min={min_values}, max={max_values})")