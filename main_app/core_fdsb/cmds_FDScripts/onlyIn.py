# cmds_FDScripts/onlyIn.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDAbortScript, _send_error
)


def _as_id(text: str) -> int | None:
    m = re.fullmatch(r"<#(\d+)>|(\d+)", text)
    return int(m.group(1) or m.group(2)) if m else None


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    parts = [ctx.resolve(a).strip() for a in args]
    if len(parts) < 2 or not all(parts):
        await _send_error(ch, FDSyntaxError(
            "`$onlyIn` requires at least one channel/server and an error message — "
            "example: `$onlyIn[123456789012345678;general;Error message]`"
        ))
        return

    message, entries = parts[-1], parts[:-1]
    ids = {i for i in map(_as_id, entries) if i is not None}
    names = {e for e in entries if _as_id(e) is None}

    src = ctx.interaction or ctx.message
    channel = getattr(src, "channel", None)
    guild = getattr(src, "guild", None)

    here_ids = {getattr(channel, "id", None), getattr(guild, "id", None)}
    here_names = {getattr(channel, "name", None), getattr(guild, "name", None)}

    if (ids & here_ids) or (names & here_names):
        ctx.log_event("onlyIn → Passed.")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(message)
    if sent:
        ctx.last_bot_message = sent
    ctx.log_event("onlyIn → Denied. Error message sent.")
    raise FDAbortScript()