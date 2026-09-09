# cmds_FDScripts/editSelectMenuOption.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError,
    _send_error, _truncate,
)


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
                "`$editSelectMenuOption` — the message ID (7th arg) must be a valid snowflake (numbers only)"
            ))
            return None
        try:
            return await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$editSelectMenuOption` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return None
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$editSelectMenuOption` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return None

    if ctx.interaction is not None and ctx.interaction.message is not None:
        return ctx.interaction.message

    if ctx.last_bot_message is not None:
        return ctx.last_bot_message

    await _send_error(ch, FDLogicError(
        "`$editSelectMenuOption` — no target message: provide a message ID (7th arg), "
        "or use this command inside an interaction / after sending a message"
    ))
    return None


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 4:
        await _send_error(ch, FDSyntaxError(
            "`$editSelectMenuOption` requires at least 4 arguments: "
            "`$editSelectMenuOption[Menu ID;Label;Value;Description;(Default;Emoji;Message ID)]`"
        ))
        return

    menu_id = ctx.resolve(args[0]).strip()
    label = ctx.resolve(args[1])
    value = ctx.resolve(args[2]).strip()
    description = ctx.resolve(args[3])
    default = len(args) > 4 and ctx.resolve(args[4]).strip().lower() == "yes"
    emoji = ctx.resolve(args[5]).strip() if len(args) > 5 and args[5].strip() else None
    message_id_arg = ctx.resolve(args[6]).strip() if len(args) > 6 and args[6].strip() else None

    if not menu_id:
        await _send_error(ch, FDLogicError("`$editSelectMenuOption` — the Menu ID (1st arg) cannot be empty"))
        return

    if not label.strip():
        await _send_error(ch, FDLogicError(
            "`$editSelectMenuOption` — the label (2nd arg) cannot be empty"
        ))
        return

    if not value:
        await _send_error(ch, FDLogicError(
            "`$editSelectMenuOption` — the value (3rd arg) cannot be empty; "
            "it must match the value of the option you want to edit"
        ))
        return

    if ctx.bot.user is None:
        await _send_error(ch, FDLogicError("`$editSelectMenuOption` — bot user is unavailable"))
        return

    target_message = await _fetch_target_message(ch, ctx, message_id_arg)
    if target_message is None:
        return

    if target_message.author.id != ctx.bot.user.id:
        await _send_error(ch, FDLogicError(
            "`$editSelectMenuOption` — the target message must have been sent by this bot"
        ))
        return

    existing_view = discord.ui.View.from_message(target_message, timeout=None)

    select: discord.ui.Select | None = None
    other_items = []
    for item in existing_view.children:
        if isinstance(item, discord.ui.Select) and item.custom_id == menu_id:
            select = item
        else:
            other_items.append(item)

    if select is None:
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenuOption` — no select menu with ID `{menu_id}` was found on that message"
        ))
        return

    target_option: discord.SelectOption | None = None
    for opt in select.options:
        if opt.value == value:
            target_option = opt
            break

    if target_option is None:
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenuOption` — no option with value `{value}` exists in select menu `{menu_id}`"
        ))
        return

    if default:
        for opt in select.options:
            opt.default = False

    target_option.label = label
    target_option.description = description or None
    target_option.default = default
    target_option.emoji = emoji

    new_view = discord.ui.View(timeout=None)
    for item in other_items:
        new_view.add_item(item)
    new_view.add_item(select)

    try:
        updated_message = await target_message.edit(view=new_view)
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(
            f"`$editSelectMenuOption` — failed to update message `{target_message.id}`: `{e}`"
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
        "select": select,
        "message_id": updated_message.id,
        "added_to_view": True,
    }

    ctx.log_event(f"editSelectMenuOption → updated `{value}` in `{menu_id}` → {_truncate(label)!r}")