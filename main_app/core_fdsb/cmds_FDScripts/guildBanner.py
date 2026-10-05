# cmds_FDScripts/guildBanner.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _format_banner(guild: discord.Guild) -> str:
    key = guild.banner.key
    ext = "gif" if guild.banner.is_animated() else "png"
    return f"https://cdn.discordapp.com/banners/{guild.id}/{key}.{ext}"


def _current_guild(ctx: ExecutionContext) -> discord.Guild | None:
    if getattr(ctx, "message", None) and ctx.message.guild:
        return ctx.message.guild
    if getattr(ctx, "interaction", None) and ctx.interaction.guild:
        return ctx.interaction.guild
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    fallback = ctx.resolve(args[1]).strip() if len(args) > 1 else ""

    if guild_id_str:
        if not guild_id_str.isdigit():
            return fallback
        guild = ctx.bot.get_guild(int(guild_id_str))
    else:
        guild = _current_guild(ctx)

    if guild is None or guild.banner is None:
        return fallback

    return _format_banner(guild)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    guild = None

    if guild_id_str:
        if not guild_id_str.isdigit():
            await _send_error(ch, FDLogicError(
                f"`$guildBanner` — guild ID must be a valid snowflake (numbers only), got `{guild_id_str}`"
            ))
            return

        guild_id = int(guild_id_str)
        guild = ctx.bot.get_guild(guild_id)

        if guild is None:
            try:
                guild = await ctx.bot.fetch_guild(guild_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                guild = None

        if guild is None:
            await _send_error(ch, FDLogicError(
                f"`$guildBanner` — bot is not in a server with ID `{guild_id_str}`"
            ))
            return
    else:
        guild = _current_guild(ctx)
        if guild is None:
            await _send_error(ch, FDEnvironmentError(
                "`$guildBanner` — this command can only be used inside a server, or provide a guild ID in DMs."
            ))
            return

    if guild.banner is None:
        await _send_error(ch, FDLogicError("`$guildBanner` — that server has no banner set"))
        return

    url = _format_banner(guild)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    ctx.last_bot_message = await dest.send(url)
    ctx.log_event(f"guildBanner → {url}")