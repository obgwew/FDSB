# cmds_FDScripts/randomUserID.py
import random
import discord
from FDScript import ExecutionContext, Command, FDEnvironmentError, _send_error


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            "`$randomUserID` only works inside servers"
        ))
        return

    members = [m for m in guild.members if not m.bot]
    if not members:
        await _send_error(ch, FDEnvironmentError(
            "No human members found in this server"
        ))
        return

    chosen = random.choice(members)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    await dest.send(str(chosen.id))
    ctx.log_event(f"randomUserID → {chosen.id}")