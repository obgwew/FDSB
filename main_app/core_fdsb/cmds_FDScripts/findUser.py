# cmds_FDScripts/findUser.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error, _truncate,
)
import re

_MENTION_RE = re.compile(r"<@!?(\d+)>")
_USAGE = "`$findUser` accepts 1 or 2 arguments:\n`$findUser[User ID/mention;(Return author ID?)]`"


def _compute(args: list[str], ctx: ExecutionContext) -> tuple[str | None, tuple[type, str] | None]:
    if len(args) > 2:
        return None, (FDLogicError, _USAGE)

    user_raw = ctx.resolve(args[0]).strip() if args else ""
    flag     = ctx.resolve(args[1]).strip().lower() if len(args) > 1 else "yes"

    if flag not in ("yes", "no"):
        return None, (FDLogicError, f"`$findUser` — return author ID? must be `yes` or `no`, got: `{flag}`")

    user_id = None
    mention = _MENTION_RE.fullmatch(user_raw)
    if mention:
        user_id = int(mention.group(1))
    elif user_raw.isdigit():
        user_id = int(user_raw)

    if user_id is not None:
        guild_id = ctx.builtins.get("guildID", "")
        guild = ctx.bot.get_guild(int(guild_id)) if guild_id.isdigit() else None
        if guild is not None:
            member = guild.get_member(user_id)
            if member is not None:
                return str(member.id), None

    if flag == "no":
        return "", None

    author_id = ctx.builtins.get("authorID", "")
    if not author_id:
        return None, (
            FDEnvironmentError,
            "`$findUser` — no author is available in this context to return; use `no` for the second argument",
        )
    return author_id, None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    result, error = _compute(args, ctx)
    if error is not None:
        ctx._abort_with_error(error[0](error[1]))
    return result or ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result, error = _compute(args, ctx)
    if error is not None:
        await _send_error(ch, error[0](error[1]))
        return

    if not result:
        await _send_error(ch, FDEnvironmentError(
            "`$findUser` — no member found, so there is nothing to send"
        ))
        return

    ctx.stop_typing()
    sent = await ch.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"findUser → {_truncate(result)!r}")