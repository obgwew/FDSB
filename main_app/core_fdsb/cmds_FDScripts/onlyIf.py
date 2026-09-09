# cmds_FDScripts/onlyIf.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDAbortScript, _send_error, evaluate_condition
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        return "false"
    return "true" if evaluate_condition(args[0].strip(), ctx) else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$onlyIf` requires a condition and an error message separated by a semicolon `;` — "
            "example: `$onlyIf[x == y; Custom Error Message!]`"
        ))
        return

    cond_str = args[0].strip()

    result = evaluate_condition(cond_str, ctx)
    ctx.log_event(f"onlyIf [{cond_str}] → {'✓ Passed' if result else '✗ Failed'}")

    if not result:
        error_msg = ctx.resolve(args[1]).strip()

        ctx.stop_typing()
        if error_msg:
            dest = await ctx.get_dest()
            sent = await dest.send(error_msg)
            ctx.last_bot_message = sent

        ctx.log_event("onlyIf → Aborting script execution.")
        raise FDAbortScript()