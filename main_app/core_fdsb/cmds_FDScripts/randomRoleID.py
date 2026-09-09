# cmds_FDScripts/randomRoleID.py
import random
import discord
from FDScript import ExecutionContext, Command, FDLogicError, FDEnvironmentError, _send_error


def _get_eligible_roles(guild: discord.Guild) -> list[discord.Role]:
    return [r for r in guild.roles if not r.is_default()]


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild = ctx.message.guild
    if guild is None:
        return ""
    roles = _get_eligible_roles(guild)
    if not roles:
        return ""
    return str(random.choice(roles).id)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild = ctx.message.guild
    if guild is None:
        await _send_error(ch, FDLogicError(
            "`$randomRoleID` — this command can only be used inside a server (not in DMs)"
        ))
        return

    roles = _get_eligible_roles(guild)
    if not roles:
        await _send_error(ch, FDEnvironmentError(
            "`$randomRoleID` — this server has no roles to pick from"
        ))
        return

    role = random.choice(roles)
    result = str(role.id)

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"randomRoleID → {result} ({role.name})")