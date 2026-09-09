# cmds_FDScripts/kick.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError, _send_error
)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    
    if not guild:
        await _send_error(ch, FDEnvironmentError(
            "`$kick` can only be used inside a server (guild), not in DMs."
        ))
        return

    target_id = None

    if not args:
        target_id = ctx.message.author.id
    else:
        resolved_text = "".join(ctx.resolve(arg) for arg in args).strip()
        
        clean_id_str = re.sub(r'\D', '', resolved_text)
        
        if not clean_id_str:
            await _send_error(ch, FDLogicError(
                f"`$kick` — invalid user ID or mention: `{resolved_text}`"
            ))
            return
            
        try:
            target_id = int(clean_id_str)
        except ValueError:
            await _send_error(ch, FDLogicError(
                f"`$kick` — could not parse ID: `{resolved_text}`"
            ))
            return

    try:
        user_to_kick = discord.Object(id=target_id)
        
        await guild.kick(
            user_to_kick, 
            reason=f"Kicked via $kick command by {ctx.message.author.name}"
        )
        
        ctx.log_event(f"kick → successfully kicked user ID `{target_id}`")
        
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$kick` — user ID `{target_id}` is not currently in the server."
        ))
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$kick` — bot lacks `Kick Members` permission or the target's role is higher than the bot's."
        ))
    except discord.HTTPException as e:
        ctx.log_event(f"warning: failed to kick user `{target_id}`: `{e.text}`")
    except Exception as ex:
        ctx.log_event(f"warning: unexpected error in $kick: `{ex}`")