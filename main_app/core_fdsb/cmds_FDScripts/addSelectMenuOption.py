# cmds_FDScripts/addSelectMenuOption.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError,
    _send_error, _truncate,
)

MAX_OPTIONS = 25
MAX_COMPONENTS_PER_MESSAGE = 25


def _get_registry(ctx: ExecutionContext) -> dict:
    registry = getattr(ctx, "_select_menus", None)
    if registry is None:
        registry = {}
        setattr(ctx, "_select_menus", registry)
    return registry


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def _sync_to_message(ch: discord.abc.Messageable, ctx: ExecutionContext,
                            menu_id: str, entry: dict, message_id: int) -> bool:
    try:
        target_message = await ctx.message.channel.fetch_message(message_id)
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — no message found with ID `{message_id}` in this channel"
        ))
        return False
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — failed to fetch message `{message_id}`: `{e}`"
        ))
        return False

    if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
        await _send_error(ch, FDLogicError(
            "`$addSelectMenuOption` — the message ID must point to a message sent by this bot"
        ))
        return False

    existing_view = discord.ui.View.from_message(target_message, timeout=None)
    kept_items = [
        item for item in existing_view.children
        if not (isinstance(item, discord.ui.Select) and item.custom_id == menu_id)
    ]

    if len(kept_items) >= MAX_COMPONENTS_PER_MESSAGE:
        await _send_error(ch, FDLogicError(
            "`$addSelectMenuOption` — that message has no room left for this select menu"
        ))
        return False

    new_view = discord.ui.View(timeout=None)
    for item in kept_items:
        new_view.add_item(item)
    new_view.add_item(entry["select"])

    try:
        updated_message = await target_message.edit(view=new_view)
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — failed to update message `{message_id}`: `{e}`"
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

    entry["message_id"] = message_id
    return True


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 4:
        await _send_error(ch, FDSyntaxError(
            "`$addSelectMenuOption` requires at least 4 arguments: "
            "`$addSelectMenuOption[Menu ID;Label;Value;Description;(Default;Emoji;Message ID)]`"
        ))
        return

    menu_id = ctx.resolve(args[0]).strip()
    label = ctx.resolve(args[1])
    value = ctx.resolve(args[2]).strip()
    description = ctx.resolve(args[3])
    default = len(args) > 4 and ctx.resolve(args[4]).strip().lower() == "yes"
    emoji = ctx.resolve(args[5]).strip() if len(args) > 5 and args[5].strip() else None
    message_id_arg = ctx.resolve(args[6]).strip() if len(args) > 6 and args[6].strip() else None

    registry = _get_registry(ctx)
    entry = registry.get(menu_id)

    if entry is None:
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — no select menu with ID `{menu_id}` was created in this script "
            f"(use `$newSelectMenu` first)"
        ))
        return

    select: discord.ui.Select = entry["select"]

    if not label.strip():
        await _send_error(ch, FDLogicError(
            "`$addSelectMenuOption` — the label (2nd arg) cannot be empty"
        ))
        return

    if not value:
        await _send_error(ch, FDLogicError(
            "`$addSelectMenuOption` — the value (3rd arg) cannot be empty"
        ))
        return

    if any(opt.value == value for opt in select.options):
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — the value `{value}` is already used in select menu `{menu_id}` "
            f"(values must be unique)"
        ))
        return

    if len(select.options) >= MAX_OPTIONS:
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — select menu `{menu_id}` already has {MAX_OPTIONS} options"
        ))
        return

    if default and any(opt.default for opt in select.options):
        await _send_error(ch, FDLogicError(
            f"`$addSelectMenuOption` — select menu `{menu_id}` already has a default option "
            f"(only one default option is allowed)"
        ))
        return

    message_id: int | None = None
    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$addSelectMenuOption` — the message ID (7th arg) must be a valid snowflake (numbers only)"
            ))
            return
        message_id = int(message_id_arg)
    elif entry["message_id"] is not None:
        message_id = entry["message_id"]

    option = discord.SelectOption(
        label=label,
        value=value,
        description=description or None,
        default=default,
        emoji=emoji,
    )

    select.options.append(option)

    if message_id is not None:
        ok = await _sync_to_message(ch, ctx, menu_id, entry, message_id)
        if not ok:
            select.options.remove(option)
            return
    else:
        if ctx.view is None:
            ctx.view = discord.ui.View(timeout=None)

        if not entry["added_to_view"]:
            if len(ctx.view.children) >= MAX_COMPONENTS_PER_MESSAGE:
                select.options.remove(option)
                await _send_error(ch, FDLogicError(
                    "`$addSelectMenuOption` — no room left on the response message for this select menu"
                ))
                return
            ctx.view.add_item(select)
            entry["added_to_view"] = True

    ctx.log_event(f"addSelectMenuOption → added `{_truncate(label)}` (`{value}`) to `{menu_id}`")