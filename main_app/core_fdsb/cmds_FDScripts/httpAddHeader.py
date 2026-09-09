# cmds_FDScripts/httpAddHeader.py
import discord
from FDScript import ExecutionContext, Command, FDSyntaxError

def _process(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 2:
        ctx._abort_with_error(FDSyntaxError("`$httpAddHeader` requires 2 args: `$httpAddHeader[name; value]`"))

    if not hasattr(ctx, "http_headers"):
        ctx.http_headers = {}

    name = ctx.resolve(args[0]).strip()
    value = ctx.resolve(args[1])
    ctx.http_headers[name] = value
    return ""

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process(args, ctx)

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    _process(args, ctx)