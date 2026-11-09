# cmds_FDScripts/textCount.py
from FDScript import ExecutionContext


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    text = ";".join(args)
    count = len(text)
    ctx.log_event(f"textCount → {count}")
    return str(count)