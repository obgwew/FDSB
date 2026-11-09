# cmds_FDScripts/onlyIf.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDAbortScript, _send_error, evaluate_condition
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDSyntaxError(
            "`$onlyIf` requires a condition and a message slot — "
            "example: `$onlyIf[x == y; Custom Error Message!]` "
            "or `$onlyIf[x == y;]` for silent abort"
        ))
        return

    if not args[0].strip():
        await _send_error(ch, FDLogicError("`$onlyIf` requires a condition."))
        return

    cond_str = args[0].strip()

    result = evaluate_condition(cond_str, ctx)
    ctx.log_event(f"onlyIf [{cond_str}] → {'✓ Passed' if result else '✗ Failed'}")

    if result:
        return

    ctx.stop_typing()

    error_msg = ";".join(ctx.resolve(arg) for arg in args[1:]).strip()

    if error_msg:
        dest = await ctx.get_dest()
        sent = await dest.send(error_msg)
        if sent:
            ctx.last_bot_message = sent
        ctx.log_event("onlyIf → Failed. Custom message sent.")
    else:
        ctx.log_event("onlyIf → Failed. Silent abort.")

    ctx.log_event("onlyIf → Aborting script execution.")
    raise FDAbortScript()