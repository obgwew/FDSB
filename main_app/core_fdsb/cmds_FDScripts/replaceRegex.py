# cmds_FDScripts/replaceRegex.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

def build_pattern(rule: str) -> str:
    rule = rule.strip()
    is_exclude = False
    
    if rule.startswith('-['):
        is_exclude = True
        rule = rule[1:] 
    elif rule.startswith('+['):
        rule = rule[1:]

    if rule.startswith('[') and rule.endswith(']'):
        inner = rule[1:-1]
        parts = inner.split('-')
        
        if len(parts) > 2:
            chars = "".join(parts)
            pattern = f"[^{chars}]+" if is_exclude else f"[{chars}]+"
        else:
            pattern = f"[^{inner}]+" if is_exclude else f"[{inner}]+"
        return pattern
    
    return re.escape(rule)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 3:
        return ctx.resolve(args[0]) if args else ""
    
    text = ctx.resolve(args[0])
    pattern = build_pattern(ctx.resolve(args[1]))
    replacement = ctx.resolve(args[2])

    try:
        return re.sub(pattern, replacement, text)
    except re.error:
        return text

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDLogicError(
            "`$replaceRegex` requires 3 arguments: `$replaceRegex[text; rule; replacement]`"
        ))
        return

    text = ctx.resolve(args[0])
    pattern = build_pattern(ctx.resolve(args[1]))
    replacement = ctx.resolve(args[2])

    try:
        result = re.sub(pattern, replacement, text)
    except re.error as e:
        await _send_error(ch, FDLogicError(f"`$replaceRegex` — Invalid rule pattern: {e}"))
        return

    if not result.strip():
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"replaceRegex → Processed replacement using pattern: {pattern}")