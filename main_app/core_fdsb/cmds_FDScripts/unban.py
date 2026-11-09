# cmds_FDScripts/unban.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, FDRuntimeError, _send_error,
)

_ID_RE = re.compile(r"\d{15,25}")


def _guild_and_author(ctx: ExecutionContext):
    if ctx.interaction is not None:
        return ctx.interaction.guild, ctx.interaction.user
    msg = ctx.message
    return getattr(msg, "guild", None), getattr(msg, "author", None)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild, author = _guild_and_author(ctx)
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$unban` can only be used inside a server (guild), not in DMs."
        ))
        return

    resolved = [ctx.resolve(a) for a in args] if args else []

    raw_user = resolved[0].strip() if resolved else ""
    if not raw_user:
        await _send_error(ch, FDLogicError(
            "`$unban` requires a user ID or mention (literal or from a nested command) — "
            "example: `$unban[123456789012345678]` or `$unban[$authorID;reason]`"
        ))
        return

    m = _ID_RE.search(raw_user)
    if not m:
        await _send_error(ch, FDLogicError(
            f"`$unban` — invalid user ID or mention: `{raw_user}`"
        ))
        return
    target_id = int(m.group())

    reason = ";".join(resolved[1:]).strip() if len(resolved) > 1 else ""
    author_name = getattr(author, "name", "unknown")
    full_reason = f"{reason} (via $unban by {author_name})" if reason else f"Unbanned via $unban command by {author_name}"

    if not guild.me.guild_permissions.ban_members:
        await _send_error(ch, FDEnvironmentError("`$unban` — bot lacks the `Ban Members` permission."))
        return

    try:
        await guild.unban(discord.Object(id=target_id), reason=full_reason[:512])
        ctx.log_event(f"unban → successfully unbanned user ID `{target_id}`")
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$unban` — user ID `{target_id}` is not found in the ban list."
        ))
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$unban` — bot lacks `Ban Members` permission to perform this action."
        ))
    except discord.HTTPException as e:
        ctx.log_event(f"unban → ✗ HTTP error {e.status}: {e.text}")
        await _send_error(ch, FDRuntimeError(f"`$unban` — Discord API error: `{e.text}`"))