# cmds_FDScripts/return.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError,
    _send_error, _truncate,
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$return` requires one argument: `$return[var]`"
        ))
        return

    key = args[0].strip()
    if not key:
        await _send_error(ch, FDLogicError(
            "`$return[]` — variable name cannot be empty"
        ))
        return

    if key not in ctx.return_vars:
        await _send_error(ch, FDRuntimeError(
            f"`$return[{key}]` — `{key}` has no value stored by any `$returnXxx` command"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent: discord.Message = await dest.send(str(ctx.return_vars[key]))
    ctx.last_bot_message = sent
    ctx.log_event(f"return [{key}] → {_truncate(str(ctx.return_vars[key]))!r}")