# cmds_FDScripts/splitOut.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)

def _get_split_value(args: list[str], ctx: ExecutionContext) -> str:
    split_result = getattr(ctx, "split_result", None)
    if split_result is None:
        raise ValueError("no split result in context")

    index_raw = ctx.resolve(args[0]).strip()

    if index_raw == ">":
        index = len(split_result) - 1
    elif index_raw == "<":
        index = 0
    else:
        try:
            index = int(index_raw) - 1
        except ValueError:
            raise ValueError(f"invalid index `{index_raw}`")

    if index < 0 or index >= len(split_result):
        raise ValueError(f"index `{index_raw}` is out of range")

    return split_result[index]

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""
    try:
        return _get_split_value(args, ctx)
    except Exception:
        return "" 

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$splitOut` requires an index argument: `$splitOut[index]`\n"
            "Valid values: a number (1-based), `<` for first, `>` for last."
        ))
        return

    try:
        value = _get_split_value(args, ctx)
    except ValueError as e:
        msg = str(e)
        if "no split result" in msg:
            await _send_error(ch, FDEnvironmentError("`$splitOut` — no split result in context. Call `$splitIn` first."))
        elif "invalid index" in msg:
             await _send_error(ch, FDLogicError(f"`$splitOut` — {msg}. Use a number (1-based), `<` (first), or `>` (last)."))
        else:
            await _send_error(ch, FDLogicError(f"`$splitOut` — {msg}."))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"splitOut → `{value}`")