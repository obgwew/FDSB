# cmds_FDScripts/isAdmin.py
import discord
from FDScript import ExecutionContext, Command


def _resolve_member_sync(raw_id: str | None, ctx: ExecutionContext, guild: discord.Guild) -> discord.Member | None:
    if not raw_id:
        user = ctx.interaction.user if ctx.interaction else (ctx.message.author if ctx.message else None)
        if isinstance(user, discord.Member):
            return user
        if user:
            return guild.get_member(user.id)
        return None

    user_id_str = raw_id.strip("<@!>")
    try:
        user_id = int(user_id_str)
    except ValueError:
        return None

    return guild.get_member(user_id)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild: discord.Guild | None = None
    if ctx.interaction and ctx.interaction.guild:
        guild = ctx.interaction.guild
    elif ctx.message and ctx.message.guild:
        guild = ctx.message.guild

    if guild is None:
        return "false"

    target_raw = ctx.resolve(args[0]).strip() if args else None
    member = _resolve_member_sync(target_raw, ctx, guild)

    if member is None:
        return "false"

    if guild.owner_id == member.id:
        return "true"

    if getattr(member.guild_permissions, 'administrator', False):
        return "true"

    return "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild: discord.Guild | None = None
    if ctx.interaction and ctx.interaction.guild:
        guild = ctx.interaction.guild
    elif ctx.message and ctx.message.guild:
        guild = ctx.message.guild

    if guild is None:
        result = "false"
    else:
        target_raw = ctx.resolve(args[0]).strip() if args else None
        member = _resolve_member_sync(target_raw, ctx, guild)
        if member is None and target_raw:
            try:
                uid = int(target_raw.strip("<@!>"))
                member = await guild.fetch_member(uid)
            except Exception:
                member = None

        if member and (guild.owner_id == member.id or getattr(member.guild_permissions, 'administrator', False)):
            result = "true"
        else:
            result = "false"

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"isAdmin → {result}")