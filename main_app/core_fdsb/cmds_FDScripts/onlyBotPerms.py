# cmds_FDScripts/onlyBotPerms.py
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
            "`$onlyBotPerms` requires at least one permission and an error message — "
            "example: `$onlyBotPerms[kick_members;ban_members;Error message]`"
        ))
        return

    message, names = parts[-1], [p.lower() for p in parts[:-1]]
    for name in names:
        if name not in discord.Permissions.VALID_FLAGS:
            await _send_error(ch, FDLogicError(f"`$onlyBotPerms` — unknown permission `{name}`"))
            return

    src = ctx.interaction or ctx.message
    guild = getattr(src, "guild", None)
    channel = getattr(src, "channel", None)
    if guild is None:
        await _send_error(ch, FDEnvironmentError("`$onlyBotPerms` can only be used within a server."))
        return

    member = guild.me
    if member is None and ctx.bot and ctx.bot.user:
        try:
            member = await guild.fetch_member(ctx.bot.user.id)
        except Exception:
            member = None
    if member is None:
        await _send_error(ch, FDEnvironmentError("`$onlyBotPerms` — could not resolve the server member."))
        return

    if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
        have = channel.permissions_for(member)
    else:
        have = member.guild_permissions
    missing = [n for n in names if not getattr(have, n)]

    if not missing:
        ctx.log_event("onlyBotPerms → Passed.")
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(message)
    if sent:
        ctx.last_bot_message = sent
    ctx.log_event(f"onlyBotPerms → Denied (missing: {', '.join(missing)}). Error message sent.")
    raise FDAbortScript()