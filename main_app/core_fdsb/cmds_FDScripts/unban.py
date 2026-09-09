# cmds_FDScripts/unban.py
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
            "`$unban` can only be used inside a server (guild), not in DMs."
        ))
        return

    if not args:
        await _send_error(ch, FDLogicError(
            "`$unban` requires a user ID argument inside brackets — example: `$unban[123456789]`"
        ))
        return

    resolved_text = "".join(ctx.resolve(arg) for arg in args).strip()

    if not resolved_text.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$unban` — invalid input: `{resolved_text}`. This command strictly requires a raw numeric user ID without mentions or symbols."
        ))
        return

    target_id = int(resolved_text)

    try:
        user_to_unban = discord.Object(id=target_id)
        
        await guild.unban(
            user_to_unban,
            reason=f"Unbanned via $unban command by {ctx.message.author.name}"
        )
        
        ctx.log_event(f"unban → successfully unbanned user ID `{target_id}`")
        
    except discord.NotFound:
        await _send_error(ch, FDLogicError(
            f"`$unban` — user ID `{target_id}` is not found in the ban list."
        ))
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$unban` — bot lacks `Ban Members` permission to perform this action."
        ))
    except discord.HTTPException as e:
        ctx.log_event(f"warning: failed to unban user `{target_id}`: `{e.text}`")
    except Exception as ex:
        ctx.log_event(f"warning: unexpected error in $unban: `{ex}`")