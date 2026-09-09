# cmds_FDScripts/getBotInvent.py
import discord
from FDScript import ExecutionContext, Command


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    client_id = ctx.bot.application_id or (ctx.bot.user and ctx.bot.user.id)
    if not client_id:
        return "Error: bot application ID is not available"
    return f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot"

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    res = resolve_inline(cmd.args, ctx)
    
    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(res)
    ctx.last_bot_message = sent
    ctx.log_event("getBotInvent → generated invite link")