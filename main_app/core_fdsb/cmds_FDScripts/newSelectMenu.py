# cmds_FDScripts/newSelectMenu.py
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


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$newSelectMenu` requires at least 3 arguments: "
            "`$newSelectMenu[Menu ID;Min;Max;(Placeholder;Message ID)]`"
        ))
        return

    menu_id = ctx.resolve(args[0]).strip()
    min_str = ctx.resolve(args[1]).strip()
    max_str = ctx.resolve(args[2]).strip()
    placeholder = ctx.resolve(args[3]) if len(args) > 3 and args[3].strip() else None
    message_id_arg = ctx.resolve(args[4]).strip() if len(args) > 4 and args[4].strip() else None

    if not menu_id:
        await _send_error(ch, FDLogicError("`$newSelectMenu` — the Menu ID (1st arg) cannot be empty"))
        return

    if not min_str.isdigit() or not max_str.isdigit():
        await _send_error(ch, FDLogicError(
            "`$newSelectMenu` — Min and Max (2nd/3rd args) must be numbers"
        ))
        return

    min_values = int(min_str)
    max_values = int(max_str)

    if not (0 <= min_values <= MAX_SELECT_VALUES):
        await _send_error(ch, FDLogicError(
            f"`$newSelectMenu` — Min must be between 0 and {MAX_SELECT_VALUES}"
        ))
        return

    if not (1 <= max_values <= MAX_SELECT_VALUES):
        await _send_error(ch, FDLogicError(
            f"`$newSelectMenu` — Max must be between 1 and {MAX_SELECT_VALUES}"
        ))
        return

    if min_values > max_values:
        await _send_error(ch, FDLogicError(
            "`$newSelectMenu` — Min cannot be greater than Max"
        ))
        return

    registry = _get_registry(ctx)

    if menu_id in registry:
        await _send_error(ch, FDLogicError(
            f"`$newSelectMenu` — a select menu with ID `{menu_id}` was already created in this script "
            f"(use `$editSelectMenu` to modify an existing one)"
        ))
        return

    target_message_id: int | None = None

    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$newSelectMenu` — the message ID (5th arg) must be a valid snowflake (numbers only)"
            ))
            return

        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$newSelectMenu` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$newSelectMenu` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return

        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$newSelectMenu` — the message ID (5th arg) must point to a message sent by this bot"
            ))
            return

        existing_view = discord.ui.View.from_message(target_message, timeout=None)
        if any(
            isinstance(item, discord.ui.Select) and item.custom_id == menu_id
            for item in existing_view.children
        ):
            await _send_error(ch, FDLogicError(
                f"`$newSelectMenu` — that message already has a select menu with ID `{menu_id}`"
            ))
            return

        target_message_id = target_message.id

    select = discord.ui.Select(
        custom_id=menu_id,
        placeholder=placeholder,
        min_values=min_values,
        max_values=max_values,
        options=[],
    )

    registry[menu_id] = {
        "select": select,
        "message_id": target_message_id,
        "added_to_view": False,
    }

    suffix = f" for message {target_message_id}" if target_message_id else ""
    ctx.log_event(f"newSelectMenu → registered `{menu_id}` (min={min_values}, max={max_values}){suffix}")