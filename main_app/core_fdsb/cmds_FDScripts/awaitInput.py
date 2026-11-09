# cmds_FDScripts/awaitInput.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)
from main_app.core_fdsb.event_FDScripts.awaitedCommand import register_wait

_NAME_RE = re.compile(r"[\w-]+")
_USAGE = (
    "`$awaitInput` requires 1 to 3 arguments:\n"
    "`$awaitInput[Name;(User ID;Channel ID)]`"
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(arg).strip() for arg in args]

    if not 1 <= len(resolved) <= 3:
        await _send_error(ch, FDLogicError(_USAGE))
        return

    name     = resolved[0]
    user_raw = resolved[1] if len(resolved) > 1 else ""
    chan_raw = resolved[2] if len(resolved) > 2 else ""

    if not _NAME_RE.fullmatch(name):
        await _send_error(ch, FDLogicError(
            f"`$awaitInput` — invalid name: `{name}`\n"
            "Use letters, digits, `_` or `-` only."
        ))
        return

    if not user_raw:
        author_id = ctx.builtins.get("authorID", "")
        if not author_id.isdigit():
            await _send_error(ch, FDEnvironmentError(
                "`$awaitInput` — no user available in this context; pass a user ID or `everyone`"
            ))
            return
        user_id = int(author_id)
    elif user_raw.lower() == "everyone":
        user_id = None
    elif user_raw.isdigit():
        user_id = int(user_raw)
    else:
        await _send_error(ch, FDLogicError(
            f"`$awaitInput` — user must be a user ID or `everyone`, got: `{user_raw}`"
        ))
        return

    if not chan_raw:
        current = ctx.builtins.get("channelID", "")
        if not current.isdigit():
            await _send_error(ch, FDEnvironmentError(
                "`$awaitInput` — no channel available in this context; pass a channel ID"
            ))
            return
        channel_id = int(current)
    elif chan_raw.isdigit():
        channel_id = int(chan_raw)
        if ctx.bot.get_channel(channel_id) is None:
            await _send_error(ch, FDEnvironmentError(
                f"`$awaitInput` — channel `{channel_id}` not found or bot has no access"
            ))
            return
    else:
        await _send_error(ch, FDLogicError(
            f"`$awaitInput` — invalid channel ID: `{chan_raw}`"
        ))
        return

    register_wait(channel_id, user_id, name)
    who = "everyone" if user_id is None else f"user {user_id}"
    ctx.log_event(f"awaitInput [{name}] → waiting for {who} in channel {channel_id}")