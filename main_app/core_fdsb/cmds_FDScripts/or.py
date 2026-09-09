# cmds_FDScripts/or.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, evaluate_condition

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "false"
        
    for arg in args:
        if evaluate_condition(arg, ctx):
            return "true"
            
    return "false"

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved_args = [ctx.resolve(arg) for arg in args]
    
    res = resolve_inline(resolved_args, ctx)
    
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(res) 
    ctx.last_bot_message = sent
    ctx.log_event(f"or → {res}")