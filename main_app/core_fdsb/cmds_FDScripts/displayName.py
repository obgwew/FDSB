import discord
import re
from FDScript import ExecutionContext, Command, _resolve_dm_target

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str | None:
    if not args or not args[0].strip():
        target = ctx.interaction.user if ctx.interaction else ctx.message.author
        return target.display_name
    
    target_str = args[0].strip()
    mention_match = re.match(r'^<@!?(\d+)>$', target_str)
    
    if mention_match:
        user_id = int(mention_match.group(1))
    elif target_str.isdigit():
        user_id = int(target_str)
    else:
        return ""

    user = None
    if getattr(ctx, "message", None) and getattr(ctx.message, "guild", None):
        user = ctx.message.guild.get_member(user_id)
    if not user and ctx.bot:
        user = ctx.bot.get_user(user_id)
    
    return user.display_name if user else ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args or not args[0].strip():
        target = ctx.interaction.user if ctx.interaction else ctx.message.author
        value = target.display_name
    else:
        user = await _resolve_dm_target(args[0], ctx, ch)
        if user is None:
            return
        value = user.display_name

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(value)
    ctx.last_bot_message = sent
    
    arg_log = f"[{args[0]}]" if args and args[0].strip() else ""
    ctx.log_event(f"displayName{arg_log} → {value!r}")