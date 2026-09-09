# cmds_FDScripts/membersCount.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDRuntimeError, _send_error


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    if args and args[0]:
        try:
            guild_id = int(args[0])
        except ValueError:
            return FDLogicError("`$membersCount` — Invalid guild ID").msg
        guild = ctx.bot.get_guild(guild_id)
        if guild is None:
            return FDRuntimeError("`$membersCount` — Guild not found").msg
        include_bots = (args[1].lower() == 'yes') if len(args) >= 2 else False
    else:
        guild = ctx.message.guild if ctx.message else None
        include_bots = False

    if guild is None:
        return FDLogicError("`$membersCount` — Guild ID required (not in a server)").msg

    if include_bots:
        return str(guild.member_count)
    return str(sum(1 for m in guild.members if not m.bot))


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = None
    include_bots = False

    if not args:
        guild = ctx.message.guild
        if guild is None:
            await _send_error(ch, FDLogicError("Guild ID required."))
            return
        include_bots = False
    else:
        if len(args) < 2:
            await _send_error(ch, FDLogicError("Missing arguments."))
            return
            
        guild_id_str = args[0].strip()
        include_bots_str = args[1].strip().lower()

        try:
            guild_id = int(guild_id_str)
        except ValueError:
            await _send_error(ch, FDLogicError("Invalid ID."))
            return

        guild = ctx.bot.get_guild(guild_id)
        if guild is None:
            await _send_error(ch, FDRuntimeError("Guild not found."))
            return

        include_bots = (include_bots_str == 'yes')

    if include_bots:
        final_count = guild.member_count
    else:
        final_count = sum(1 for member in guild.members if not member.bot)

    value = str(final_count)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"membersCount → {value}")