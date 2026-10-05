# cmds_FDScripts/onlyUserPerms.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDAbortScript,
    _send_error
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    parts = [ctx.resolve(a).strip() for a in args]
    if len(parts) < 2 or not all(parts):
        await _send_error(ch, FDSyntaxError(
            "`$onlyUserPerms` requires at least one permission and an error message — "
            "example: `$onlyUserPerms[kick_members;ban_members;Error message]`"
        ))
        return

    message, names = parts[-1], [p.lower() for p in parts[:-1]]
    for name in names:
        if name not in discord.Permissions.VALID_FLAGS:
            await _send_error(ch, FDLogicError(f"`$onlyUserPerms` — unknown permission `{name}`"))
            return

    src = ctx.interaction or ctx.message
    user = getattr(src, "user", None) or getattr(src, "author", None)
    guild = getattr(src, "guild", None)
    channel = getattr(src, "channel", None)
    if guild is None:
        await _send_error(ch, FDEnvironmentError("`$onlyUserPerms` can only be used within a server."))
        return

    member = user if isinstance(user, discord.Member) else guild.get_member(user.id)
    if member is None and user is not None:
        try:
            member = await guild.fetch_member(user.id)
        except Exception:
            member = None
    if member is None:
        await _send_error(ch, FDEnvironmentError("`$onlyUserPerms` — could not resolve the server member."))
        return

    if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
        have = channel.permissions_for(member)
    else:
        have = member.guild_permissions
    missing = [n for n in names if not getattr(have, n)]

    if not missing:
        ctx.log_event("onlyUserPerms → Passed.")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(message)
    if sent:
        ctx.last_bot_message = sent
    ctx.log_event(f"onlyUserPerms → Denied (missing: {', '.join(missing)}). Error message sent.")
    raise FDAbortScript()