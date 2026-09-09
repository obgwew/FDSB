# cmds_FDScripts/serverIcon.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def _format_icon(asset: discord.Asset) -> str:
    fmt = "gif" if asset.is_animated() else "png"
    return asset.with_format(fmt).url


def _resolve_icon_url(guild_id_str: str, ctx: ExecutionContext) -> str | None:
    if not guild_id_str:
        guild = ctx.message.guild
    else:
        if not guild_id_str.isdigit():
            return None
        guild = ctx.bot.get_guild(int(guild_id_str))

    if guild is None or guild.icon is None:
        return None

    return _format_icon(guild.icon)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    return _resolve_icon_url(guild_id_str, ctx) or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    url = _resolve_icon_url(guild_id_str, ctx)

    if url is None:
        if guild_id_str and not guild_id_str.isdigit():
            await _send_error(ch, FDLogicError(
                f"`$serverIcon` — guild ID must be a valid snowflake (numbers only), got `{guild_id_str}`"
            ))
            return

        if guild_id_str:
            guild = ctx.bot.get_guild(int(guild_id_str))
            if guild is None:
                await _send_error(ch, FDLogicError(
                    f"`$serverIcon` — bot is not in a server with ID `{guild_id_str}`"
                ))
                return

        await _send_error(ch, FDLogicError(
            "`$serverIcon` — that server has no icon set"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(url)
    ctx.last_bot_message = sent
    ctx.log_event(f"serverIcon → {url}")