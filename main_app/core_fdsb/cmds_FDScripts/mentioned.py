# cmds_FDScripts/mentioned.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError,
    _send_error,
)

_USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
_YES = {"yes", "y", "true", "1", "on"}
_NO = {"no", "n", "false", "0", "off"}


def _author_mention(ctx: ExecutionContext) -> str:
    m = ctx.builtins.get("mentioned")
    if m:
        return str(m)
    author_id = ctx.builtins.get("authorID")
    return f"<@{author_id}>" if author_id else ""


def _mentioned_ids(ctx: ExecutionContext) -> list[str]:
    if ctx.interaction is not None or ctx.message is None:
        return []
    content = getattr(ctx.message, "content", "") or ""
    seen: list[str] = []
    for uid in _USER_MENTION_RE.findall(content):
        if uid not in seen:
            seen.append(uid)
    return seen


def _compute(args: list[str], ctx: ExecutionContext):
    if len(args) > 2:
        return None, FDSyntaxError("`$mentioned` — takes at most 2 arguments: `$mentioned[n;yes/no]`")

    index_raw = args[0].strip() if len(args) >= 1 else ""
    flag_raw = args[1].strip().lower() if len(args) >= 2 else ""

    if index_raw == "":
        index = 1
    elif index_raw.isdigit() and int(index_raw) >= 1:
        index = int(index_raw)
    else:
        return None, FDLogicError(
            f"`$mentioned` — the mention number must be a positive integer (got `{index_raw}`)"
        )

    if flag_raw == "" or flag_raw in _YES:
        return_author = True
    elif flag_raw in _NO:
        return_author = False
    else:
        return None, FDLogicError(
            f"`$mentioned` — 'return author' must be yes or no (got `{flag_raw}`)"
        )

    ids = _mentioned_ids(ctx)
    if index <= len(ids):
        return f"<@{ids[index - 1]}>", None
    return (_author_mention(ctx) if return_author else ""), None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    value, err = _compute(args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
    ctx.log_event(f"mentioned → {value!r}")
    return value


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    resolved = [ctx.resolve(a) for a in args]
    value, err = _compute(resolved, ctx)
    if err is not None:
        await _send_error(ch, err)
        return

    if not value:
        ctx.log_event("mentioned → nobody mentioned and return-author is 'no'; nothing sent")
        return

    ctx.stop_typing()
    sent = await ch.send(value)
    if sent is not None:
        ctx.last_bot_message = sent
    ctx.log_event(f"mentioned → {value}")