# cmds_FDScripts/removeComponent.py
import asyncio
import discord
from FDScript import ExecutionContext, Command
from FDCore import FDSyntaxError, FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""

def _find_component(view: discord.ui.View, target_id: str):
    for item in view.children:
        if isinstance(item, discord.ui.Button) and (item.custom_id == target_id or item.url == target_id):
            return item
        if isinstance(item, discord.ui.Select) and item.custom_id == target_id:
            return item
    return None

def _forget_select_menu(ctx: ExecutionContext, target_id: str) -> None:
    registry = getattr(ctx, "_select_menus", None)
    if registry is not None:
        registry.pop(target_id, None)

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
            print(f"[FDScript - removeComponent] Async edit failed: {e}")

    ctx._view_edit_task = asyncio.create_task(_commit_edit())

def _split_ids_and_message(args: list[str]) -> tuple[list[str], str | None]:
    cleaned = [a.strip() for a in args if a.strip()]
    if len(cleaned) >= 2 and cleaned[-1].isdigit():
        return cleaned[:-1], cleaned[-1]
    return cleaned, None

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(arg).strip() for arg in args if arg.strip()]

    if len(resolved_args) < 1:
        await _send_error(ch, FDSyntaxError(
            "`$removeComponent` requires at least 1 argument: "
            "`$removeComponent[customID1; customID2; ...; (messageID)]`"
        ))
        return

    target_ids, message_id_arg = _split_ids_and_message(resolved_args)

    if not target_ids:
        await _send_error(ch, FDLogicError(
            "`$removeComponent` — at least one custom ID/URL/Menu ID must be provided"
        ))
        return

    if message_id_arg is not None:
        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except (discord.NotFound, ValueError):
            await _send_error(ch, FDLogicError(
                f"`$removeComponent` — no message found with ID `{message_id_arg}`"
            ))
            return
        
        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$removeComponent` — the message ID must point to a message sent by this bot"
            ))
            return

        view = discord.ui.View.from_message(target_message, timeout=None)
        removed, missing = [], []
        for tid in target_ids:
            component = _find_component(view, tid)
            if component is not None:
                view.remove_item(component)
                removed.append(tid)
                _forget_select_menu(ctx, tid)
            else:
                missing.append(tid)

        if not removed:
            await _send_error(ch, FDLogicError(f"`$removeComponent` — none of the given IDs `{', '.join(target_ids)}` were found"))
            return

        try:
            await target_message.edit(view=view)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeComponent` — failed to edit message: `{e}`"))
            return

        ctx.log_event(f"$removeComponent → removed [{', '.join(removed)}] from message {message_id_arg}")
        return

    if ctx.view is not None:
        removed, missing = [], []
        for tid in target_ids:
            component = _find_component(ctx.view, tid)
            if component is not None:
                ctx.view.remove_item(component)
                removed.append(tid)
                _forget_select_menu(ctx, tid)
            else:
                missing.append(tid)

        if removed:
            ctx.log_event(f"$removeComponent → removed [{', '.join(removed)}] from pending view")
            if ctx.last_bot_message:
                _reschedule_debounced_edit(ctx)
            return

    if ctx.interaction is not None and ctx.interaction.message is not None:
        source_message = ctx.interaction.message
        view = discord.ui.View.from_message(source_message, timeout=None)
        removed, missing = [], []
        for tid in target_ids:
            component = _find_component(view, tid)
            if component is not None:
                view.remove_item(component)
                removed.append(tid)
                _forget_select_menu(ctx, tid)
            else:
                missing.append(tid)

        if not removed:
            await _send_error(ch, FDLogicError(f"`$removeComponent` — none of the given IDs `{', '.join(target_ids)}` were found"))
            return

        try:
            await source_message.edit(view=view)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeComponent` — failed to edit interaction message: `{e}`"))
            return

        ctx.log_event(f"$removeComponent → removed [{', '.join(removed)}] from interaction message")
        return

    await _send_error(ch, FDLogicError("`$removeComponent` — no context found to perform removal."))