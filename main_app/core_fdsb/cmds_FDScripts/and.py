# cmds_FDScripts/and.py
import discord
from FDScript import ExecutionContext, Command, evaluate_condition

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return "false"
        
    for arg in args:
        if not evaluate_condition(arg, ctx):
            return "false"
            
    return "true"

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    res = resolve_inline(cmd.args, ctx)
    
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(res) 
    ctx.last_bot_message = sent
    ctx.log_event(f"and → {res}")