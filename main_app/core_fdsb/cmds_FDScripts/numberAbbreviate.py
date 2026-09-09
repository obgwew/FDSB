# cmds_FDScripts/numberAbbreviate.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_INTEGER_RE = re.compile(r"^[+-]?\d+$")

_SUFFIXES = ["", "k", "m", "b", "t", "qa", "qi", "sx", "sp", "oc", "no", "dc"]


def _abbreviate(value: int) -> str:
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    digit_str = str(abs_value)

    if abs_value < 1000:
        return f"{sign}{digit_str}"

    tier = (len(digit_str) - 1) // 3
    max_tier = len(_SUFFIXES) - 1

    if tier > max_tier:
        return f"{sign}{digit_str}"

    shift = 3 * tier
    integer_part = digit_str[:-shift]
    frac_part = digit_str[-shift:].rstrip("0")

    if frac_part:
        return f"{sign}{integer_part}.{frac_part}{_SUFFIXES[tier]}"
    return f"{sign}{integer_part}{_SUFFIXES[tier]}"


def _parse_and_abbreviate(number_str: str) -> str | None:
    number_str = number_str.strip()
    if not _INTEGER_RE.match(number_str):
        return None
    return _abbreviate(int(number_str))


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""
    number_str = ctx.resolve(args[0]).strip()
    return _parse_and_abbreviate(number_str) or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$numberAbbreviate` requires 1 argument: $numberAbbreviate[number]"
        ))
        return

    number_str = ctx.resolve(args[0]).strip()
    result = _parse_and_abbreviate(number_str)

    if result is None:
        await _send_error(ch, FDLogicError(
            f"`$numberAbbreviate` — `{number_str}` is not a valid whole number "
            f"(decimals and non-numeric characters are not supported)"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"numberAbbreviate → {result!r} (input={number_str})")