# cmds_FDScripts/isBot.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "false"

    raw = ctx.resolve(args[0]).strip()

    guild: discord.Guild | None = getattr(ctx.message, "guild", None)
    if guild is None:
        return "false"

    user_id_str = raw.strip("<@!>")
    try:
        user_id = int(user_id_str)
    except ValueError:
        return "false"

    member: discord.Member | None = guild.get_member(user_id)
    if member is None:
        return "false"

    return "true" if member.bot else "false"


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$isBot` requires a user ID or mention argument: `$isBot[userID]`"
        ))
        return

    result = resolve_inline(cmd.args, ctx)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"isBot → {result} for user `{ctx.resolve(args[0]).strip()}`")