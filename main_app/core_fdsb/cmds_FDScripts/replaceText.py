# cmds_FDScripts/replaceText.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, _send_error
)

def resolve_inline(args: list, ctx: ExecutionContext) -> str:
    if len(args) < 3:
        return ""

    resolved = [ctx.resolve(arg) for arg in args]
    message   = resolved[0]
    old_text  = resolved[1]
    new_text  = resolved[2]
    amount    = int(resolved[3]) if len(resolved) >= 4 and resolved[3].strip().lstrip('-').isdigit() else -1

    return message.replace(old_text, new_text, amount) if amount >= 0 else message.replace(old_text, new_text)


async def execute(cmd: Command, args: list, ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDLogicError(
            "`$replaceText` requires at least 3 arguments — "
            "example: `$replaceText[message; old; new]` or `$replaceText[message; old; new; 2]`"
        ))
        return

    resolved = [ctx.resolve(arg) for arg in args]
    message  = resolved[0]
    old_text = resolved[1]
    new_text = resolved[2]

    amount = -1
    if len(resolved) >= 4:
        amount_str = resolved[3].strip()
        if not amount_str.lstrip('-').isdigit():
            await _send_error(ch, FDLogicError(
                f"`$replaceText` — invalid amount: `{amount_str}`. Use a number or `-1` for all."
            ))
            return
        amount = int(amount_str)

    result = message.replace(old_text, new_text, amount) if amount >= 0 else message.replace(old_text, new_text)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent

    ctx.log_event(f"replaceText → replaced '{old_text}' with '{new_text}' (amount: {amount})")