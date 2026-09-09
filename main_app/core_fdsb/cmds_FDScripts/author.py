# cmds_FDScripts/author.py
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error, _truncate

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        index = 1
        if len(args) > 1:
            idx_str = ctx.resolve(args[1]).strip()
            if idx_str.isdigit():
                index = int(idx_str)
        
        resolved_text = ctx.resolve(args[0])
        embed = ctx.get_embed_builder(index)
        
        current_url = embed.author.url if embed.author else None
        current_icon = embed.author.icon_url if embed.author else None
        
        embed.set_author(name=resolved_text, url=current_url, icon_url=current_icon)
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) in (1, 2):
        index = 1
        if len(args) == 2:
            idx_str = ctx.resolve(args[1]).strip()
            if not idx_str.isdigit():
                await _send_error(ch, FDLogicError("`$author` index must be a number: $author[text;index]"))
                return
            index = int(idx_str)
            
        resolved_text = ctx.resolve(args[0])
        embed = ctx.get_embed_builder(index)
        
        current_url = embed.author.url if embed.author else None
        current_icon = embed.author.icon_url if embed.author else None
        
        embed.set_author(name=resolved_text, url=current_url, icon_url=current_icon)
        ctx.log_event(f"author → {_truncate(resolved_text)!r} (index {index})")
    else:
        await _send_error(ch, FDLogicError("`$author` requires 1-2 arguments: $author[text;index (optional)]"))