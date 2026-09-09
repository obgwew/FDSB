# cmds_FDScripts/clear.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDRuntimeError, FDEnvironmentError,
    _send_error, _CLEAR_DEFAULT, _CLEAR_MAX,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        limit: int = _CLEAR_DEFAULT
    else:
        raw_limit = args[0].strip()

        if not raw_limit.lstrip("-").isdigit():
            await _send_error(ch, FDLogicError(
                f"`$clear` — expected an integer between `1` and `{_CLEAR_MAX}`, "
                f"got: `{raw_limit}`"
            ))
            return

        parsed = int(raw_limit)

        if parsed < 1:
            await _send_error(ch, FDLogicError(
                f"`$clear` — value must be at least `1`, got: `{parsed}`"
            ))
            return

        if parsed > _CLEAR_MAX:
            await _send_error(ch, FDLogicError(
                f"`$clear` — value `{parsed}` exceeds the maximum allowed (`{_CLEAR_MAX}`). "
                f"Discord's bulk delete limit is 100 messages per request."
            ))
            return

        limit = parsed

    try:
        deleted = await ch.purge(limit=limit)
        ctx.log_event(f"clear [{limit}] → deleted {len(deleted)} message(s)")
    except discord.Forbidden:
        ctx.log_event("clear → ✗ no permission")
        await _send_error(ch, FDEnvironmentError(
            "`$clear` — bot lacks `Manage Messages` permission in this channel"
        ))
    except discord.HTTPException as e:
        ctx.log_event(f"clear → ✗ HTTP error: {e.status}")
        await _send_error(ch, FDRuntimeError(
            f"`$clear` — Discord API error: `{e.text}`"
        ))