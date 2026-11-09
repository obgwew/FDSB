# cmds_FDScripts/ban.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError, _send_error,
)

_ID_RE = re.compile(r"\d{15,25}")


def _guild_and_author(ctx: ExecutionContext):
    if ctx.interaction is not None:
        return ctx.interaction.guild, ctx.interaction.user
    msg = ctx.message
    return getattr(msg, "guild", None), getattr(msg, "author", None)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild, author = _guild_and_author(ctx)
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$ban` can only be used inside a server (guild), not in DMs."
        ))
        return

    if len(args) > 2:
        await _send_error(ch, FDSyntaxError(
            f"`$ban` — takes at most 2 arguments `$ban[user;reason]`, got {len(args)}"
        ))
        return

    if not args or not ctx.resolve(args[0]).strip():
        if author is None:
            await _send_error(ch, FDLogicError("`$ban` — no user given and no author to fall back to"))
            return
        target_id = author.id
    else:
        raw_user = ctx.resolve(args[0]).strip()
        m = _ID_RE.search(raw_user)
        if not m:
            await _send_error(ch, FDLogicError(
                f"`$ban` — invalid user ID or mention: `{raw_user}`"
            ))
            return
        target_id = int(m.group())

    reason = ctx.resolve(args[1]).strip() if len(args) > 1 else ""
    author_name = getattr(author, "name", "unknown")
    full_reason = f"{reason} (via $ban by {author_name})" if reason else f"Banned via $ban command by {author_name}"

    if not guild.me.guild_permissions.ban_members:
        await _send_error(ch, FDEnvironmentError("`$ban` — bot lacks the `Ban Members` permission."))
        return

    try:
        await guild.ban(discord.Object(id=target_id), reason=full_reason[:512])
        ctx.log_event(f"ban → successfully banned user ID `{target_id}`")
    except discord.NotFound:
        await _send_error(ch, FDLogicError(f"`$ban` — user ID `{target_id}` does not exist."))
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$ban` — bot lacks `Ban Members` permission or the target's role is higher than the bot's."
        ))
    except discord.HTTPException as e:
        ctx.log_event(f"ban → ✗ HTTP error {e.status}: {e.text}")
        await _send_error(ch, FDRuntimeError(f"`$ban` — Discord API error: `{e.text}`"))