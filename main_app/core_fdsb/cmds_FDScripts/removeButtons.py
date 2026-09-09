# cmds_FDScripts/removeButtons.py
import asyncio
import discord
from FDScript import ExecutionContext, Command
from FDCore import FDLogicError, _send_error


def _reschedule_debounced_edit(ctx: ExecutionContext) -> None:
    if getattr(ctx, '_view_edit_task', None) and not ctx._view_edit_task.done():
        ctx._view_edit_task.cancel()

    async def _commit_edit():
        try:
            await asyncio.sleep(0.25)
            ctx.last_bot_message = await ctx.last_bot_message.edit(view=ctx.view)
        except asyncio.CancelledError:
            pass
        except discord.HTTPException as e:
            print(f"[FDScript - removeButtons] Async edit failed: {e}")

    ctx._view_edit_task = asyncio.create_task(_commit_edit())


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(a).strip() for a in (args or []) if a and a.strip()]
    message_id_arg = resolved_args[0] if resolved_args else None

    if message_id_arg is not None:
        if not message_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$removeButtons` — the message ID (1st arg) must be a valid snowflake (numbers only)"
            ))
            return

        try:
            target_message = await ctx.message.channel.fetch_message(int(message_id_arg))
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$removeButtons` — no message found with ID `{message_id_arg}` in this channel"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$removeButtons` — failed to fetch message `{message_id_arg}`: `{e}`"
            ))
            return

        if ctx.bot.user is None or target_message.author.id != ctx.bot.user.id:
            await _send_error(ch, FDLogicError(
                "`$removeButtons` — the message ID (1st arg) must point to a message sent by this bot"
            ))
            return

        try:
            await target_message.edit(view=None)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(
                f"`$removeButtons` — failed to edit message `{message_id_arg}`: `{e}`"
            ))
            return

        ctx.log_event(f"$removeButtons → cleared all buttons on message {message_id_arg}")
        return

    if ctx.view is not None and len(ctx.view.children) > 0:
        ctx.view.clear_items()
        ctx.log_event("$removeButtons → cleared all buttons from pending view")

        if getattr(ctx, 'last_bot_message', None) is not None:
            _reschedule_debounced_edit(ctx)
        return

    if ctx.interaction is not None and ctx.interaction.message is not None:
        source_message = ctx.interaction.message
        try:
            await source_message.edit(view=None)
        except discord.HTTPException as e:
            await _send_error(ch, FDLogicError(f"`$removeButtons` — failed to edit the source message: `{e}`"))
            return

        ctx.log_event("$removeButtons → cleared all buttons on interaction source message")
        return

    await _send_error(ch, FDLogicError(
        "`$removeButtons` — nothing queued yet, and no messageID / interaction context to look in"
    ))