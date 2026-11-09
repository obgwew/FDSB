# cmds_FDScripts/untimeout.py
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
    resolved = [ctx.resolve(a) for a in args] if args else []

    user_str = resolved[0].strip() if resolved else ""
    if not user_str:
        await _send_error(ch, FDLogicError(
            "`$untimeout` requires a user mention or ID (literal or from a nested command) — "
            "example: `$untimeout[@user]` or `$untimeout[$authorID;reason]`"
        ))
        return

    m = _ID_RE.search(user_str)
    if not m:
        await _send_error(ch, FDLogicError(
            f"`$untimeout` — could not parse user from: `{user_str}`. Please provide a valid mention or User ID."
        ))
        return
    user_id = int(m.group())

    reason = ";".join(resolved[1:]).strip() if len(resolved) > 1 else ""

    guild, author = _guild_and_author(ctx)
    if guild is None:
        await _send_error(ch, FDEnvironmentError("`$untimeout` can only be used within a server (guild)."))
        return

    if not guild.me.guild_permissions.moderate_members:
        await _send_error(ch, FDEnvironmentError("`$untimeout` — bot lacks the `Moderate Members` permission."))
        return

    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            await _send_error(ch, FDLogicError(
                f"`$untimeout` — user with ID `{user_id}` was not found in this server."
            ))
            return
        except discord.HTTPException as ex:
            ctx.log_event(f"untimeout → ✗ could not fetch member {user_id}: {ex}")
            await _send_error(ch, FDRuntimeError(f"`$untimeout` — Discord API error: `{ex.text}`"))
            return

    if member.top_role >= guild.me.top_role and member.id != guild.me.id:
        await _send_error(ch, FDEnvironmentError(
            f"`$untimeout` — `{member.name}`'s highest role is not below the bot's role; move the bot's role higher."
        ))
        return

    if getattr(member, "timed_out_until", None) is None:
        ctx.log_event(f"untimeout → {member.name} ({user_id}) is not timed out; nothing to do")
        return

    author_name = getattr(author, "name", "unknown")
    full_reason = f"{reason} (via $untimeout by {author_name})" if reason else f"FDScript untimeout invoked by {author_name}"

    try:
        await member.timeout(None, reason=full_reason[:512])
        ctx.log_event(f"untimeout → removed timeout from {member.name} ({user_id})")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            f"`$untimeout` — bot lacks permission to remove timeout from `{member.name}`. "
            "Ensure the bot has 'Moderate Members' permission and its highest role is above the target user."
        ))
    except discord.HTTPException as ex:
        ctx.log_event(f"untimeout → ✗ HTTP error {ex.status}: {ex.text}")
        await _send_error(ch, FDRuntimeError(f"`$untimeout` — Discord API error: `{ex.text}`"))