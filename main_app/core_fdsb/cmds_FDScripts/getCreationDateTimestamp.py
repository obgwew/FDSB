# cmds_FDScripts/getCreationDateTimestamp.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""
    
    raw_id = ctx.resolve(args[0]).strip()
    id_str = re.sub(r'[<@!#&>]', '', raw_id)
    
    if not id_str.isdigit():
        return ""
        
    try:
        target_id = int(id_str)
        created_at = discord.utils.snowflake_time(target_id)
        return str(int(created_at.timestamp()))
    except (ValueError, OSError, OverflowError):
        return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 1:
        await _send_error(ch, FDLogicError(
            "`$getCreationDateTimestamp` requires 1 argument: `$getCreationDateTimestamp[id or mention]`"
        ))
        return
        
    raw_id = ctx.resolve(args[0]).strip()
    id_str = re.sub(r'[<@!#&>]', '', raw_id)
    
    if not id_str.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$getCreationDateTimestamp` — Invalid ID or mention '{raw_id}'."
        ))
        return
        
    try:
        target_id = int(id_str)
        created_at = discord.utils.snowflake_time(target_id)
        result = str(int(created_at.timestamp()))
    except (ValueError, OSError, OverflowError):
        await _send_error(ch, FDLogicError(
            f"`$getCreationDateTimestamp` — Could not parse time from ID '{raw_id}'."
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"getCreationDateTimestamp → Extracted timestamp {result} for ID {target_id}")