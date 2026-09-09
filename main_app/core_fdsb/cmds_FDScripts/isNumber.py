# cmds_FDScripts/isNumber.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def _check(formula: str, value: str) -> bool:
    f = formula.strip().lower()
    v = value.strip()

    match f:

        case "int":
            try:
                int(v)
                return "." not in v
            except ValueError:
                return False

        case "nat":
            try:
                n = int(v)
                return n >= 1 and "." not in v
            except ValueError:
                return False

        case "pos":
            try:
                return float(v) > 0
            except ValueError:
                return False

        case "neg":
            try:
                return float(v) < 0
            except ValueError:
                return False

        case "zero":
            try:
                return float(v) == 0
            except ValueError:
                return False

        case "even":
            try:
                n = int(v)
                return "." not in v and n % 2 == 0
            except ValueError:
                return False

        case "odd":
            try:
                n = int(v)
                return "." not in v and n % 2 != 0
            except ValueError:
                return False

        case "dec":
            try:
                float(v)
                return "." in v
            except ValueError:
                return False

        case "frac":
            match_ = re.fullmatch(r"-?\d+\s*/\s*-?\d+", v)
            if not match_:
                return False
            parts = v.split("/")
            return int(parts[1].strip()) != 0

        case "num":
            try:
                float(v)
                return True
            except ValueError:
                return False

        case _:
            return False

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        return "false"

    formula = ctx.resolve(args[0])
    value   = ctx.resolve(args[1])

    return "true" if _check(formula, value) else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDLogicError(
            "`$isNumber` requires two arguments: `$isNumber[formula; value]`\n"
            "Formulas: `int` `nat` `pos` `neg` `zero` `even` `odd` `dec` `frac` `num`"
        ))
        return

    result = resolve_inline(cmd.args, ctx)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(
        f"isNumber → {result} "
        f"(formula=`{ctx.resolve(args[0])}` value=`{ctx.resolve(args[1])}`)"
    )