# cmds_FDScripts/guildBanner.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _format_banner(asset: discord.Asset) -> str:
    fmt = "gif" if asset.is_animated() else "png"
    return asset.with_format(fmt).url


def _resolve_banner_url(guild_id_str: str, ctx: ExecutionContext) -> str | None:
    guild = None

    if not guild_id_str:
        if getattr(ctx, "message", None) and ctx.message.guild:
            guild = ctx.message.guild
        elif getattr(ctx, "interaction", None) and ctx.interaction.guild:
            guild = ctx.interaction.guild
    else:
        if not guild_id_str.isdigit():
            return None
        guild = ctx.bot.get_guild(int(guild_id_str))

    if guild is None or guild.banner is None:
        return None

    return _format_banner(guild.banner)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    return _resolve_banner_url(guild_id_str, ctx) or ""


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
        if getattr(ctx, "message", None) and ctx.message.guild:
            guild = ctx.message.guild
        elif getattr(ctx, "interaction", None) and ctx.interaction.guild:
            guild = ctx.interaction.guild

        if guild is None:
            await _send_error(ch, FDEnvironmentError(
                "`$guildBanner` — this command can only be used inside a server, or provide a guild ID in DMs."
            ))
            return

    if guild.banner is None:
        await _send_error(ch, FDLogicError(
            "`$guildBanner` — that server has no banner set"
        ))
        return

    url = _format_banner(guild.banner)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(url)
    ctx.last_bot_message = sent
    ctx.log_event(f"guildBanner → {url}")