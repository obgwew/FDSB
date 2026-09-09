# cmds_FDScripts/findRole.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_MENTION_RE = re.compile(r"^<@&(\d+)>$")


def _find_role(guild: discord.Guild, query: str) -> discord.Role | None:
    query = query.strip()
    if not query:
        return None

    mention_match = _MENTION_RE.match(query)
    if mention_match:
        return guild.get_role(int(mention_match.group(1)))

    if query.isdigit():
        role = guild.get_role(int(query))
        if role is not None:
            return role

    exact = discord.utils.get(guild.roles, name=query)
    if exact is not None:
        return exact

    lowered = query.lower()
    for role in guild.roles:
        if role.name.lower() == lowered:
            return role

    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args or not "".join(args).strip():
        raise FDLogicError("`$findRole` requires a role name or mention")

    if ctx.message.guild is None:
        raise FDLogicError("`$findRole` — this command can't be used outside a server")

    query = "".join(ctx.resolve(arg) for arg in args)
    role = _find_role(ctx.message.guild, query)

    if role is None:
        raise FDLogicError(f"`$findRole` — no role found matching `{query}`")

    return str(role.id)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    try:
        res = resolve_inline(cmd.args, ctx)
    except FDLogicError as e:
        await _send_error(ch, e)
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(res)
    ctx.last_bot_message = sent
    ctx.log_event(f"findRole → {res}")