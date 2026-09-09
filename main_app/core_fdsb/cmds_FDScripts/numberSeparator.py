# cmds_FDScripts/numberSeparator.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_INTEGER_RE = re.compile(r"^-?\d+$")
_DEFAULT_SEPARATOR = ","


def _format_number(number_str: str, separator: str) -> str | None:
    number_str = number_str.strip()
    if not _INTEGER_RE.match(number_str):
        return None

    negative = number_str.startswith("-")
    digits = number_str[1:] if negative else number_str

    groups: list[str] = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)

    result = separator.join(groups)
    return f"-{result}" if negative else result


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""

    number_str = ctx.resolve(args[0]).strip()
    separator = ctx.resolve(args[1]).strip() if len(args) > 1 and args[1].strip() else _DEFAULT_SEPARATOR

    formatted = _format_number(number_str, separator)
    return formatted or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$numberSeparator` requires at least 1 argument: $numberSeparator[number; separator (optional)]"
        ))
        return

    number_str = ctx.resolve(args[0]).strip()
    separator = ctx.resolve(args[1]).strip() if len(args) > 1 and args[1].strip() else _DEFAULT_SEPARATOR

    formatted = _format_number(number_str, separator)

    if formatted is None:
        await _send_error(ch, FDLogicError(
            f"`$numberSeparator` — `{number_str}` is not a valid whole number "
            f"(decimals and non-numeric characters are not supported)"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(formatted)
    ctx.last_bot_message = sent
    ctx.log_event(f"numberSeparator → {formatted!r} (sep={separator!r})")