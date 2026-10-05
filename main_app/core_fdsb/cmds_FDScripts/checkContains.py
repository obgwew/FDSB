# cmds_FDScripts/checkContains.py
import discord
from FDScript import (
    ExecutionContext,
    Command,
    FDSyntaxError,
    FDEnvironmentError,
    _send_error,
)


def _check_contains(text: str, phrases: list[str]) -> bool:
    for phrase in phrases:
        if not phrase:
            if not text:
                return True
            continue

        if phrase in text or (phrase.strip() and phrase.strip() in text):
            return True

    return False


def _evaluate_check_contains(args: list[str], ctx: ExecutionContext) -> str:
    text = ctx.resolve(args[0])
    phrases = [ctx.resolve(arg) for arg in args[1:]]
    return "true" if _check_contains(text, phrases) else "false"


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(
            FDSyntaxError(
                "`$checkContains` requires at least 2 arguments: `$checkContains[Text;Phrases;...]`"
            )
        )
        return "false"

    return _evaluate_check_contains(args, ctx)


async def execute(
    cmd: Command,
    args: list[str],
    ctx: ExecutionContext,
    ch: discord.abc.Messageable,
) -> None:
    if len(args) < 2:
        await _send_error(
            ch,
            FDSyntaxError(
                "`$checkContains` requires at least 2 arguments: `$checkContains[Text;Phrases;...]`"
            ),
        )
        return

    result = _evaluate_check_contains(args, ctx)

    ctx.stop_typing()
    dest = await ctx.get_dest()

    try:
        sent = await dest.send(result)
        ctx.last_bot_message = sent
        ctx.log_event(f"checkContains → {result}")
    except discord.Forbidden:
        await _send_error(
            ch,
            FDEnvironmentError(
                "`$checkContains` — bot lacks permission to send messages in this channel."
            ),
        )
        return
    except discord.HTTPException as e:
        ctx.log_event(f"warning: failed to send checkContains output: `{e.text}`")
        return