# cmds_FDScripts/randomint.py
import random
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDRuntimeError, _send_error


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) == 2:
        try:
            a, b = int(float(args[0])), int(float(args[1]))
            random.seed()
            result = random.randint(min(a, b), max(a, b))
            ctx.stop_typing()
            dest = await ctx.get_dest()
            await dest.send(str(result))
            ctx.log_event(f"randomint [{min(a,b)}..{max(a,b)}] → {result}")
        except Exception:
            await _send_error(ch, FDRuntimeError(
                "`$randomint` expects numbers: $randomint[min; max]"
            ))
    else:
        await _send_error(ch, FDLogicError(
            "`$randomint` requires two arguments: $randomint[min; max]"
        ))