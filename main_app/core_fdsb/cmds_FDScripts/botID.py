# cmds_FDScripts/botID.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, _send_error


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.bot.user:
        await _send_error(ch, FDEnvironmentError("`$botID` — bot user is not available"))
        return
    value = str(ctx.bot.user.id)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"botID → {value}")