# cmds_FDScripts/authorIcon.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        index = 1
        if len(args) > 1:
            idx_str = ctx.resolve(args[1]).strip()
            if idx_str.isdigit():
                index = int(idx_str)
                
        resolved_url = ctx.resolve(args[0])
        embed = ctx.get_embed_builder(index)
        
        current_name = embed.author.name if (embed.author and embed.author.name) else "\u200b"
        current_url = embed.author.url if embed.author else None
        
        embed.set_author(name=current_name, url=current_url, icon_url=resolved_url)
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) in (1, 2):
        index = 1
        if len(args) == 2:
            idx_str = ctx.resolve(args[1]).strip()
            if not idx_str.isdigit():
                await _send_error(ch, FDLogicError("`$authorIcon` index must be a number: $authorIcon[url;index]"))
                return
            index = int(idx_str)
            
        resolved_url = ctx.resolve(args[0])
        embed = ctx.get_embed_builder(index)
        
        current_name = embed.author.name if (embed.author and embed.author.name) else "\u200b"
        current_url = embed.author.url if embed.author else None
        
        embed.set_author(name=current_name, url=current_url, icon_url=resolved_url)
        ctx.log_event(f"authorIcon → {_truncate(resolved_url)!r} (index {index})")
    else:
        await _send_error(ch, FDLogicError("`$authorIcon` requires 1-2 arguments: $authorIcon[url;index (optional)]"))