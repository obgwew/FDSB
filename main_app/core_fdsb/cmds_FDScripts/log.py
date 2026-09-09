# cmds_FDScripts/log.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    channel_id_str = ctx.resolve(args[0]).strip() if args else ""
    name_code      = ctx.resolve(args[1]).strip() if len(args) > 1 else ""

    if not channel_id_str:
        await _send_error(ch, FDLogicError(
            "`$log` requires at least a channel ID: "
            "`$log[channelID]` or `$log[channelID; name_code]`"
        ))
        return

    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$log` — invalid channel ID: `{channel_id_str}`"
        ))
        return

    ctx.snapshot_log(channel_id, name_code)
    ctx.log_event(
        f"log [{name_code or 'unnamed'}] → snapshot taken "
        f"({len(ctx._pending_logs[-1].entries)} event(s)), "
        f"will send to channel {channel_id}"
    )