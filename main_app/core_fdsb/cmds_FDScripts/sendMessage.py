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