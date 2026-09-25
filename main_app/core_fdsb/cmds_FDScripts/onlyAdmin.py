# cmds_FDScripts/onlyAdmin.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDEnvironmentError, FDAbortScript,
    _send_error
)

async def _resolve_member(ctx: ExecutionContext, guild: discord.Guild) -> discord.Member | None:
    user = None
    if ctx.interaction and ctx.interaction.user:
        user = ctx.interaction.user
    elif ctx.message and ctx.message.author:
        user = ctx.message.author

    if user is None:
        return None

    if isinstance(user, discord.Member):
        return user

    member = guild.get_member(user.id)
    if member is None:
        try:
            member = await guild.fetch_member(user.id)
        except Exception:
            member = None
    return member


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild: discord.Guild | None = None
    if ctx.interaction and ctx.interaction.guild:
        guild = ctx.interaction.guild
    elif ctx.message and ctx.message.guild:
        guild = ctx.message.guild

    if not guild:
        await _send_error(ch, FDEnvironmentError("`$onlyAdmin` can only be used within a server."))
        return

    member = await _resolve_member(ctx, guild)
    if not member:
        await _send_error(ch, FDEnvironmentError("`$onlyAdmin` — could not resolve server member."))
        return

    is_owner = (member.id == guild.owner_id)
    is_admin = getattr(member.guild_permissions, 'administrator', False)

    if not (is_owner or is_admin):
        ctx.stop_typing()

        error_msg = ";".join(ctx.resolve(arg) for arg in args).strip() if args else ""

        dest = await ctx.get_dest()
        if error_msg:
            sent = await dest.send(error_msg)
            ctx.last_bot_message = sent
            ctx.log_event(f"onlyAdmin → Denied for {member.id}. Custom error sent.")
            raise FDAbortScript()
        else:
            ctx.log_event(f"onlyAdmin → Denied for {member.id}. Default error sent.")
            await _send_error(
                dest,
                FDEnvironmentError("`$onlyAdmin` — Only server administrators or the server owner can execute this command.")
            )
            return

    ctx.log_event(f"onlyAdmin → Passed for user {member.id}.")