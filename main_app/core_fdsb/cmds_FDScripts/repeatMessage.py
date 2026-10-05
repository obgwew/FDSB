# cmds_FDScripts/repeatMessage.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
)

_DISCORD_MESSAGE_LIMIT = 2000


def _validate(args: list[str], amount_raw: str):
    if len(args) < 2:
        return FDSyntaxError("`$repeatMessage` requires two arguments: `$repeatMessage[amount; message]`")
    if not amount_raw:
        return FDLogicError("`$repeatMessage` — amount cannot be empty")
    try:
        amount = int(amount_raw)
    except ValueError:
        return FDLogicError(f"`$repeatMessage` — amount must be a whole number (got `{amount_raw}`)")
    if amount < 1:
        return FDLogicError(f"`$repeatMessage` — amount must be at least 1 (got `{amount}`)")

    unit = len(_message_text(args[1:]))
    total = unit * amount
    if total > _DISCORD_MESSAGE_LIMIT:
        return FDEnvironmentError(
            f"`$repeatMessage` — the repeated text would be {total:,} characters "
            f"({amount:,} × {unit:,}), which exceeds the {_DISCORD_MESSAGE_LIMIT:,}-character "
            f"limit of a Discord message. Use a smaller amount or a shorter message."
        )
    return None


def _message_text(message_parts: list[str]) -> str:
    return ";".join(message_parts).replace("\\s", " ")


def _build(amount_raw: str, message_parts: list[str]) -> str:
    return _message_text(message_parts) * int(amount_raw)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    amount_raw = args[0].strip() if args else ""
    err = _validate(args, amount_raw)
    if err is not None:
        ctx._abort_with_error(err)
    result = _build(amount_raw, args[1:])
    ctx.log_event(f"repeatMessage → {amount_raw}× {_truncate(args[1] if len(args) > 1 else '')!r}")
    return result


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(a) for a in args]
    amount_raw = resolved[0].strip() if resolved else ""
    err = _validate(resolved, amount_raw)
    if err is not None:
        await _send_error(ch, err)
        return

    result = _build(amount_raw, resolved[1:])
    if not result.strip():
        ctx.log_event("repeatMessage → empty message, nothing to send")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    if sent is not None:
        ctx.last_bot_message = sent
    ctx.log_event(f"repeatMessage → sent {amount_raw}× {_truncate(resolved[1] if len(resolved) > 1 else '')!r}")