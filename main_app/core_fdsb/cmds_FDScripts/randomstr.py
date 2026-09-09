# cmds_FDScripts/randomstr.py
import random
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if args:
        random.seed()
        chosen = random.choice(args)
        ctx.stop_typing()
        dest = await ctx.get_dest()
        await dest.send(chosen)
        ctx.log_event(f"randomstr [{len(args)} options] → {_truncate(chosen)!r}")
    else:
        await _send_error(ch, FDLogicError(
            "`$randomstr` requires at least one string"
        ))