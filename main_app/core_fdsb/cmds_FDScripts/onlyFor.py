# cmds_FDScripts/onlyFor.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDAbortScript, _send_error
)


def _as_id(text: str) -> int | None:
    m = re.fullmatch(r"<@[!&]?(\d+)>|(\d+)", text)
    return int(m.group(1) or m.group(2)) if m else None


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    parts = [ctx.resolve(a).strip() for a in args]
    if len(parts) < 2 or not all(parts):
        await _send_error(ch, FDSyntaxError(
            "`$onlyFor` requires at least one user/role and an error message — "
            "example: `$onlyFor[123456789012345678;Moderator;Error message]`"
        ))
        return

    message, entries = parts[-1], parts[:-1]
    ids = {i for i in map(_as_id, entries) if i is not None}
    names = {e for e in entries if _as_id(e) is None}

    src = ctx.interaction or ctx.message
    user = getattr(src, "user", None) or getattr(src, "author", None)
    guild = getattr(src, "guild", None)

    allowed = user is not None and (user.id in ids or user.name in names)

    if not allowed and user is not None and guild is not None:
        member = user if isinstance(user, discord.Member) else guild.get_member(user.id)
        if member is None:
            try:
                member = await guild.fetch_member(user.id)
            except Exception:
                member = None
        if member is not None:
            allowed = any(r.id in ids or r.name in names for r in member.roles)

    if allowed:
        ctx.log_event(f"onlyFor → Passed for user {user.id}.")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(message)
    if sent:
        ctx.last_bot_message = sent
    ctx.log_event("onlyFor → Denied. Error message sent.")
    raise FDAbortScript()