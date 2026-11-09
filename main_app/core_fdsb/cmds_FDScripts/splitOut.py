# cmds_FDScripts/splitOut.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)


def _resolve_split_out(args: list[str], ctx: ExecutionContext) -> tuple[str | None, Exception | None]:
    split_result = getattr(ctx, "split_result", None)
    if split_result is None:
        return None, FDEnvironmentError("`$splitOut` — no split result in context. Call `$splitIn` first.")

    if not args:
        return None, FDSyntaxError(
            "`$splitOut` requires an index argument: `$splitOut[index]`\n"
            "Valid values: a number (1-based), `<`, or `>`."
        )

    index_raw = ctx.resolve(args[0]).strip()
    if not index_raw:
        return None, FDLogicError("`$splitOut` — index argument cannot be empty.")

    if index_raw == ">":
        index = len(split_result) - 1
    elif index_raw == "<":
        index = 0
    else:
        try:
            index = int(index_raw) - 1
        except ValueError:
            return None, FDLogicError(
                f"`$splitOut` — invalid index `{index_raw}`. Use a number (1-based), `<` (first), or `>` (last)."
            )

    if index < 0 or index >= len(split_result):
        return None, FDLogicError(f"`$splitOut` — index `{index_raw}` is out of range.")

    return split_result[index], None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    value, err = _resolve_split_out(args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
        return ""
    return value


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    value, err = _resolve_split_out(args, ctx)
    if err is not None:
        await _send_error(ch, err)
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"splitOut → `{value}`")