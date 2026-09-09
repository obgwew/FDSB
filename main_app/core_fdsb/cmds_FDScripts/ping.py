# cmds_FDScripts/ping.py
import discord
from FDScript import ExecutionContext, Command


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    latency_ms = round(ctx.bot.latency * 1000)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    await dest.send(f"{latency_ms}")
    ctx.log_event(f"ping → {latency_ms}ms")