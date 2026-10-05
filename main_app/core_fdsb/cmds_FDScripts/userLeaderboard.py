# cmds_FDScripts/userLeaderboard.py
import discord
from FDScript import ExecutionContext, Command, _send_error
from engine_FDScript import fd_leaderboard_ops as lb

_NAME = "userLeaderboard"
_TYPE = "user"


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    text, err = lb.board_text(_NAME, _TYPE, args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
        return ""
    return text


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    text, err = lb.board_text(_NAME, _TYPE, args, ctx)
    if err is not None:
        await _send_error(ch, err)
        return
    if not text:
        ctx.log_event(f"{_NAME} → nothing to send (no ranked entries)")
        return
    ctx.stop_typing()
    sent = await ch.send(text)
    ctx.last_bot_message = sent