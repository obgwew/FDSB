# cmds_FDScripts/uptime.py
import time
import discord
from FDScript import (
    ExecutionContext, Command,
    FDEnvironmentError, _send_error,
    _BOT_START_TIME, _format_uptime,
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if _BOT_START_TIME == 0.0:
        await _send_error(ch, FDEnvironmentError(
            "`$uptime` — bot start time was never set. "
            "Make sure `set_bot_start_time()` is called in `on_ready`."
        ))
        return
    uptime_str = _format_uptime(time.time() - _BOT_START_TIME)
    ctx.stop_typing()
    dest = await ctx.get_dest()
    await dest.send(uptime_str)
    ctx.log_event(f"uptime → {uptime_str}")