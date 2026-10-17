# cmds_FDScripts/log.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error,
)

_TRUE  = {"true", "yes"}
_FALSE = {"false", "no"}

_USAGE = "`$log[channelID;(file: true/false);(name)]`"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or len(args) > 3:
        await _send_error(ch, FDLogicError(f"`$log` expects 1-3 arguments: {_USAGE}"))
        return

    channel_id_str = ctx.resolve(args[0]).strip()
    file_raw       = ctx.resolve(args[1]).strip().lower() if len(args) > 1 else ""
    name_code      = ctx.resolve(args[2]).strip() if len(args) > 2 else ""

    if not channel_id_str:
        await _send_error(ch, FDLogicError(f"`$log` requires a channel ID: {_USAGE}"))
        return

    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$log` — invalid channel ID: `{channel_id_str}`"
        ))
        return

    # file=true  -> normal message (code block) while it fits, file only when it is too long
    # file=false -> always a .txt file (also the default when omitted)
    if file_raw == "" or file_raw in _FALSE:
        prefer_message = False
    elif file_raw in _TRUE:
        prefer_message = True
    else:
        await _send_error(ch, FDLogicError(
            f"`$log` — `file` must be true or false, got `{file_raw}`. Usage: {_USAGE}"
        ))
        return

    ctx.snapshot_log(channel_id, name_code, prefer_message)
    ctx.log_event(
        f"log [{name_code or 'unnamed'}] → snapshot taken "
        f"({len(ctx._pending_logs[-1].entries)} event(s)), "
        f"will send to channel {channel_id} as {'message (file if too long)' if prefer_message else 'file'}"
    )