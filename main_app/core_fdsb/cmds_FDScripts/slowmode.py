# cmds_FDScripts/slowmode.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(arg) for arg in args]

    if len(resolved_args) < 2:
        await _send_error(ch, FDLogicError(
            "Usage: `$slowmode[channelID; time]` (e.g., `$slowmode[12345; 2h]` or `$slowmode[12345; 0s]`)"
        ))
        return

    channel_str = resolved_args[0].strip()
    time_str = resolved_args[1].strip()

    match_channel = re.search(r"(\d+)", channel_str)
    if not match_channel:
        await _send_error(ch, FDLogicError(f"`$slowmode` — invalid channel ID: `{channel_str}`"))
        return

    channel_id = int(match_channel.group(1))

    target_channel = ctx.bot.get_channel(channel_id)
    if not target_channel:
        try:
            target_channel = await ctx.bot.fetch_channel(channel_id)
        except discord.NotFound:
            await _send_error(ch, FDLogicError(f"`$slowmode` — channel `{channel_id}` not found."))
            return
        except discord.HTTPException:
            await _send_error(ch, FDEnvironmentError(f"`$slowmode` — failed to fetch channel `{channel_id}`."))
            return

    if not hasattr(target_channel, 'edit') or not hasattr(target_channel, 'slowmode_delay'):
        await _send_error(ch, FDLogicError(f"`$slowmode` — channel `{target_channel.name}` does not support slowmode."))
        return

    match_time = re.match(r"^(\d+)([smh])$", time_str.lower())
    if not match_time:
        await _send_error(ch, FDLogicError(f"`$slowmode` — invalid time format: `{time_str}`. Use s, m, or h."))
        return

    amount = int(match_time.group(1))
    unit = match_time.group(2)
    multipliers = {'s': 1, 'm': 60, 'h': 3600}
    seconds = amount * multipliers[unit]

    if seconds > 21600:
        await _send_error(ch, FDLogicError("`$slowmode` — duration cannot exceed 6 hours (21600 seconds)."))
        return

    try:
        await target_channel.edit(slowmode_delay=seconds)
        ctx.log_event(f"slowmode → set channel {target_channel.id} delay to {seconds}s")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(f"`$slowmode` — bot lacks 'Manage Channels' permission for `{target_channel.name}`."))
    except discord.HTTPException as ex:
        await _send_error(ch, FDEnvironmentError(f"`$slowmode` — HTTP error: {ex}"))