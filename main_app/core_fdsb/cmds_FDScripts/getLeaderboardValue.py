# cmds_FDScripts/getLeaderboardValue.py
import discord
from FDScript import ExecutionContext, Command, _send_error
from engine_FDScript import fd_leaderboard_ops as lb

_NAME = "getLeaderboardValue"


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    result, err = lb.board_value(_NAME, args, ctx)
    if err is not None:
        ctx._abort_with_error(err)
        return ""
    return result


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    result, err = lb.board_value(_NAME, args, ctx)
    if err is not None:
        await _send_error(ch, err)
        return
    if result == "":
        return
    ctx.stop_typing()
    sent = await ch.send(result)
    ctx.last_bot_message = sent