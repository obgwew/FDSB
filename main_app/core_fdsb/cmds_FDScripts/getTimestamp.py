# cmds_FDScripts/getTimestamp.py
import time
from FDScript import ExecutionContext

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return str(int(time.time()))