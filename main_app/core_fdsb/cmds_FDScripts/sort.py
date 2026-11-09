# cmds_FDScripts/sort.py
from decimal import Decimal, InvalidOperation
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError,
    _send_error, _parse_separator, _truncate,
)

_DIRECTIONS = {"asc", "desc"}
_USAGE = (
    "`$sort` requires at least 4 arguments:\n"
    "`$sort[Numbers;...;Direction;Return amount;Separator]`"
)


def _compute(args: list[str], ctx: ExecutionContext) -> tuple[str | None, str | None]:
    if len(args) < 4:
        return None, _USAGE

    *num_args, dir_raw, amount_raw, sep_raw = args

    direction  = ctx.resolve(dir_raw).strip().lower()
    amount_str = ctx.resolve(amount_raw).strip()
    separator  = _parse_separator(ctx.resolve(sep_raw))

    if direction not in _DIRECTIONS:
        return None, (
            f"`$sort` — direction must be `asc` or `desc`, got: `{direction}`"
        )

    try:
        amount = int(amount_str)
    except ValueError:
        return None, (
            f"`$sort` — return amount must be an integer, got: `{amount_str}`"
        )
    if amount != -1 and amount < 1:
        return None, (
            f"`$sort` — return amount must be `-1` (all) or a positive integer, got: `{amount}`"
        )

    tokens = [t.strip() for a in num_args for t in ctx.resolve(a).split(";")]

    parsed: list[tuple[Decimal, str]] = []
    for token in tokens:
        try:
            value = Decimal(token)
        except InvalidOperation:
            return None, f"`$sort` — `{token}` is not a valid number"
        if not value.is_finite():
            return None, f"`$sort` — `{token}` is not a valid number"
        parsed.append((value, token))

    parsed.sort(key=lambda p: p[0], reverse=(direction == "desc"))
    selected = parsed if amount == -1 else parsed[:amount]

    return separator.join(token for _, token in selected), None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    result, error = _compute(args, ctx)
    if error is not None:
        ctx._abort_with_error(FDLogicError(error))
    return result or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result, error = _compute(args, ctx)
    if error is not None:
        await _send_error(ch, FDLogicError(error))
        return

    ctx.stop_typing()
    sent = await ch.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"sort → {_truncate(result)!r}")