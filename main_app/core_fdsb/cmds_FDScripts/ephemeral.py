# cmds_FDScripts/ephemeral.py
import discord
from FDScript import ExecutionContext, Command

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    state = True
    if args and args[0].strip():
        val = ctx.resolve(args[0]).strip().lower()
        if val in ("false", "no", "0", "off"):
            state = False

    ctx.ephemeral = state
    if state and ctx.interaction is not None:
        ctx.queue_inline_action(ctx._prepare_ephemeral())
    return ""

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    state = True
    if args and args[0].strip():
        val = ctx.resolve(args[0]).strip().lower()
        if val in ("false", "no", "0", "off"):
            state = False

    ctx.ephemeral = state

    if not state:
        ctx.log_event("ephemeral → set to public (ephemeral disabled)")
        return

    if ctx.interaction is not None:
        await ctx._prepare_ephemeral()
        ctx.log_event("ephemeral → the response will only be visible to the user")
    else:
        ctx.log_event("ephemeral → ignored (not an interaction; only slash commands/components support it)")