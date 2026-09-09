# cmds_FDScripts/httpResult.py
import discord
import json
from FDScript import ExecutionContext, Command

def _process(args: list[str], ctx: ExecutionContext) -> str:
    result = getattr(ctx, "http_result", "")

    if not args:
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result)

    if isinstance(result, (dict, list)):
        current_val = result
        for key_raw in args:
            key = ctx.resolve(key_raw).strip()
            try:
                if isinstance(current_val, list) and key.isdigit():
                    current_val = current_val[int(key)]
                elif isinstance(current_val, dict):
                    current_val = current_val.get(key)
                else:
                    return ""
            except (KeyError, IndexError):
                return ""

            if current_val is None:
                return ""

        if isinstance(current_val, (dict, list)):
            return json.dumps(current_val, ensure_ascii=False)
        return str(current_val)

    return ""

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return _process(args, ctx)

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    res = _process(args, ctx)
    ctx.text_buffer += res