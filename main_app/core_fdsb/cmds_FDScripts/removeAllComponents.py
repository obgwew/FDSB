# cmds_FDScripts/removeAllComponents.py
import asyncio
import discord
from FDScript import ExecutionContext, Command
from FDCore import FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

def _forget_select_menus_for(ctx: ExecutionContext, message_id: int | None) -> None:
    registry = getattr(ctx, "_select_menus", None)
    if not registry:
        return
    for menu_id in list(registry.keys()):
        if registry[menu_id].get("message_id") == message_id:
            del registry[menu_id]

def _reschedule_debounced_edit(ctx: ExecutionContext) -> None:
    if getattr(ctx, '_view_edit_task', None) and not ctx._view_edit_task.done():
        ctx._view_edit_task.cancel()

    async def _commit_edit():
        try:
            await asyncio.sleep(0.25)
            if ctx.last_bot_message:
                ctx.last_bot_message = await ctx.last_bot_message.edit(view=ctx.view)
        except asyncio.CancelledError:
            pass
        except discord.HTTPException as e:
            print(f"[FDScript - removeAllComponents] Async edit failed: {e}")

    ctx._view_edit_task = asyncio.create_task(_commit_edit())

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(arg).strip() for arg in args if arg.strip()]
    message_id_arg = resolved_args[0] if resolved_args else None

    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$removeAllComponents` — the message ID must be a valid snowflake (numbers only)"
            ))
            return

        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except (discord.NotFound, discord.HTTPException):
            await _send_error(ch, FDLogicError(
                f"`$removeAllComponents` — no message found with ID `{message_id_arg}`"
            ))
            return

        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$removeAllComponents` — the message ID must point to a message sent by this bot"
            ))
            return

        try:
            updated_message = await target_message.edit(view=None)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeAllComponents` — failed to edit message: `{e}`"))
            return

        _forget_select_menus_for(ctx, updated_message.id)

        if ctx.last_bot_message is not None and ctx.last_bot_message.id == updated_message.id:
            ctx.last_bot_message = updated_message
        if (
            ctx.interaction is not None
            and ctx.interaction.message is not None
            and ctx.interaction.message.id == updated_message.id
        ):
            ctx.interaction.message = updated_message

        ctx.log_event(f"$removeAllComponents → cleared all components from message {message_id_arg}")
        return

    # No explicit message ID given — clear whatever's still queued for the bot's
    # own upcoming/last response before falling back to other contexts.
    if ctx.view is not None and len(ctx.view.children) > 0:
        _forget_select_menus_for(ctx, None)
        ctx.view = discord.ui.View(timeout=None)

        ctx.log_event("$removeAllComponents → cleared pending view")
        if ctx.last_bot_message:
            _reschedule_debounced_edit(ctx)
        return

    if ctx.interaction is not None and ctx.interaction.message is not None:
        source_message = ctx.interaction.message
        try:
            updated_message = await source_message.edit(view=None)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeAllComponents` — failed to edit interaction message: `{e}`"))
            return

        _forget_select_menus_for(ctx, updated_message.id)

        if ctx.interaction.message.id == updated_message.id:
            ctx.interaction.message = updated_message
        if ctx.last_bot_message is not None and ctx.last_bot_message.id == updated_message.id:
            ctx.last_bot_message = updated_message

        ctx.log_event("$removeAllComponents → cleared all components from interaction message")
        return

    if ctx.last_bot_message is not None:
        try:
            updated_message = await ctx.last_bot_message.edit(view=None)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeAllComponents` — failed to edit message: `{e}`"))
            return

        _forget_select_menus_for(ctx, updated_message.id)
        ctx.last_bot_message = updated_message

        ctx.log_event("$removeAllComponents → cleared all components from last bot message")
        return

    await _send_error(ch, FDLogicError("`$removeAllComponents` — no context found to perform removal."))