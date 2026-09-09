# cmds_FDScripts/charCount.py
import unicodedata
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def _count_chars(text: str) -> int:
    count = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            count += 1
        elif cat == "Nd" and "0" <= ch <= "9":
            count += 1
    return count


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "0"
    text = ctx.resolve(args[0])
    return str(_count_chars(text))


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$charCount` requires a text argument: `$charCount[text]`"
        ))
        return

    text = ctx.resolve(args[0])
    result = str(_count_chars(text))

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"charCount → {result} char(s) in `{text}`")