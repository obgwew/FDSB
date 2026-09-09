# cmds_FDScripts/sendMessage.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) == 1:
        ctx.stop_typing()
        resolved_text = ctx.resolve(args[0])

        view = ctx.view if ctx.view is not None else discord.utils.MISSING
        sent = await ch.send(resolved_text, view=view)
        ctx.view = None

        ctx.last_bot_message = sent
        ctx.log_event(f"sendMessage → {_truncate(resolved_text)!r}")
    else:
        await _send_error(ch, FDLogicError(
            "`$sendMessage` requires one argument: $sendMessage[text]"
        ))


async def _do_inline_send(ctx: ExecutionContext, resolved_text: str) -> None:
    ctx.stop_typing()
    ch = await ctx.get_dest()

    view = ctx.view if ctx.view is not None else discord.utils.MISSING
    try:
        sent = await ch.send(resolved_text, view=view)
    except discord.HTTPException as e:
        ctx.log_event(f"Failed to send inline $sendMessage: {e}")
        return
    ctx.view = None

    ctx.last_bot_message = sent
    ctx.log_event(f"sendMessage (inline) → {_truncate(resolved_text)!r}")


def resolve_inline(args: list[str], ctx: ExecutionContext) -> "str | None":
    if len(args) != 1:
        return None

    resolved_text = args[0]

    ctx.queue_inline_action(_do_inline_send(ctx, resolved_text))

    return resolved_text