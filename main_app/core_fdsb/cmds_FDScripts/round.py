# cmds_FDScripts/round.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""

    raw = ctx.resolve(args[0]).strip()

    try:
        return str(round(float(raw)))
    except ValueError:
        return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$round` requires a number argument: `$round[1.7]`"
        ))
        return

    raw = ctx.resolve(args[0]).strip()

    try:
        result = str(round(float(raw)))
    except ValueError:
        await _send_error(ch, FDLogicError(
            f"`$round` — `{raw}` is not a valid number"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"round → {raw} => {result}")