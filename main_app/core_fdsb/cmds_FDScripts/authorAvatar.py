# cmds_FDScripts/authorAvatar.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def _format_avatar(asset: discord.Asset) -> str:
    fmt = "gif" if asset.is_animated() else "png"
    return asset.with_format(fmt).url


def _global_avatar(user) -> discord.Asset:
    return user.avatar or user.default_avatar


def _resolve_avatar_url(user_id_str: str, ctx: ExecutionContext) -> str | None:
    if not user_id_str:
        return _format_avatar(_global_avatar(ctx.message.author))

    if not user_id_str.isdigit():
        return None

    user_id = int(user_id_str)

    member = ctx.message.guild.get_member(user_id) if ctx.message.guild else None
    if member is not None:
        return _format_avatar(_global_avatar(member))

    user = ctx.bot.get_user(user_id)
    if user is not None:
        return _format_avatar(_global_avatar(user))

    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    user_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    return _resolve_avatar_url(user_id_str, ctx) or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    user_id_str = ctx.resolve(args[0]).strip() if args and args[0].strip() else ""
    url = _resolve_avatar_url(user_id_str, ctx)

    if url is None:
        if not user_id_str.isdigit():
            await _send_error(ch, FDLogicError(
                f"`$authorAvatar` — user ID must be a valid snowflake (numbers only), got `{user_id_str}`"
            ))
            return

        try:
            user = await ctx.bot.fetch_user(int(user_id_str))
            url = _format_avatar(_global_avatar(user))
        except (discord.NotFound, discord.HTTPException):
            await _send_error(ch, FDLogicError(
                f"`$authorAvatar` — no user found with ID `{user_id_str}`"
            ))
            return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(url)
    ctx.last_bot_message = sent
    ctx.log_event(f"authorAvatar → {url}")