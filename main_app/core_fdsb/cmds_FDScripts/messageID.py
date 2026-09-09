# cmds_FDScripts/messageID.py
import discord
from FDScript import ExecutionContext, Command


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    value = str(ctx.message.id)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    ctx.log_event(f"messageID → {value}")