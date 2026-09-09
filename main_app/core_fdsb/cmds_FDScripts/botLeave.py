# cmds_FDScripts/botLeave.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild_id_arg = ctx.resolve(args[0]).strip() if args and args[0].strip() else None

    if guild_id_arg is None:
        target_guild = ctx.message.guild
        if target_guild is None:
            await _send_error(ch, FDLogicError(
                "`$botLeave` — this command can't be used outside a server without a guild ID"
            ))
            return
    else:
        if not guild_id_arg.isdigit():
            await _send_error(ch, FDLogicError(
                "`$botLeave` — the guild ID (1st arg) must be a valid snowflake (numbers only)"
            ))
            return

        target_guild = ctx.bot.get_guild(int(guild_id_arg))
        if target_guild is None:
            await _send_error(ch, FDLogicError(
                f"`$botLeave` — bot is not a member of guild `{guild_id_arg}`"
            ))
            return

    guild_name = target_guild.name
    guild_id = target_guild.id

    try:
        await target_guild.leave()
    except discord.HTTPException as e:
        await _send_error(ch, FDEnvironmentError(
            f"`$botLeave` — failed to leave guild `{guild_id}`: `{e}`"
        ))
        return

    ctx.log_event(f"botLeave → left guild {guild_name} ({guild_id})")