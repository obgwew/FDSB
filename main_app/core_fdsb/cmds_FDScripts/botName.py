# cmds_FDScripts/botName.py
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, _send_error


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not ctx.bot.user:
        await _send_error(ch, FDEnvironmentError("`$botName` — bot user is not available"))
        return
    value = ctx.bot.user.name
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"botName → {value!r}")