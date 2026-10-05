# cmds_FDScripts/onlyIf.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDAbortScript, _send_error, evaluate_condition
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        await _send_error(ch, FDLogicError(
            "`$onlyIf` requires a condition — "
            "example: `$onlyIf[x == y; Custom Error Message!]`"
        ))
        return

    cond_str = args[0].strip()

    result = evaluate_condition(cond_str, ctx)
    ctx.log_event(f"onlyIf [{cond_str}] → {'✓ Passed' if result else '✗ Failed'}")

    if result:
        return

    ctx.stop_typing()

    error_msg = ";".join(ctx.resolve(arg) for arg in args[1:]).strip() if len(args) > 1 else ""

    dest = await ctx.get_dest()
    if error_msg:
        sent = await dest.send(error_msg)
        ctx.last_bot_message = sent
        ctx.log_event("onlyIf → Failed. Custom error sent.")
    else:
        ctx.log_event("onlyIf → Failed. Default error sent.")
        await _send_error(
            dest,
            FDLogicError(f"`$onlyIf` — Condition failed: `{cond_str}`")
        )

    ctx.log_event("onlyIf → Aborting script execution.")
    raise FDAbortScript()