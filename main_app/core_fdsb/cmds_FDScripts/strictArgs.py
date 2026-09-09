# cmds_FDScripts/strictArgs.py
import re
import discord
from main_app.core_fdsb.FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDAbortScript,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) != 2:
        await _send_error(ch, FDLogicError(
            "`$strictArgs` requires two arguments: `$strictArgs[comparison; error_message]`\n"
            "Example: `$strictArgs[>2; Please provide more than 2 words]`"
        ))

    constraint = args[0].strip()
    error_msg  = args[1].strip()

    m = re.match(r'^(>|<|!)?(\d+)$', constraint)
    if not m:
        await _send_error(ch, FDLogicError(
            f"`$strictArgs` — invalid format: `{constraint}`\n"
            f"Valid examples: `2` `>2` `<2` `!2`"
        ))

    op  = m.group(1) or '='
    num = int(m.group(2))

    if ctx.is_event:
        word_count = len(ctx.message.content.strip().split())
    else:
        full       = ctx.message.content.strip()
        parts      = full.split(None, 1)
        args_str   = parts[1] if len(parts) > 1 else ""
        word_count = len(args_str.split()) if args_str.strip() else 0

    ok = {
        '>': word_count >  num,
        '<': word_count <  num,
        '=': word_count == num,
        '!': word_count != num,
    }[op]

    ctx.log_event(f"strictArgs [{constraint}] → {'✓' if ok else '✗'} ({word_count} words)")

    if not ok:
        ctx.stop_typing()
        dest = await ctx.get_dest()
        if error_msg:
            sent = await dest.send(error_msg)
            ctx.last_bot_message = sent
        else:
            await dest.send("❌ Invalid arguments.")
        ctx.log_event(f"strictArgs [{constraint}] → Failed. Aborting script execution.")
        raise FDAbortScript()