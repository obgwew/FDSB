# cmds_FDScripts/not.py
from FDScript import (
    ExecutionContext,
    _find_comparison_operator, _strip_quotes,
)

_TRUE_WORDS = {"true", "yes", "y", "on", "1"}
_FALSE_WORDS = {"false", "no", "n", "off", "0"}


def _compare(left: str, op: str, right: str) -> bool:
    left, right = _strip_quotes(left), _strip_quotes(right)
    try:
        l, r = float(left), float(right)
    except ValueError:
        l, r = left, right
    if op == "==":           return l == r
    if op in ("!=", "=!"):   return l != r
    if op in (">=", "=>"):   return l >= r
    if op in ("<=", "=<"):   return l <= r
    if op == ">":            return l > r
    if op == "<":            return l < r
    return False


def _to_bool(expr: str) -> bool:
    expr = expr.strip()
    if not expr:
        return False

    comp = _find_comparison_operator(expr)
    if comp is not None:
        left, op, right = comp
        return _compare(left.strip(), op, right.strip())

    low = _strip_quotes(expr).strip().lower()
    if low in _TRUE_WORDS:
        return True
    if low in _FALSE_WORDS or low == "":
        return False
    return True


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    expr = ";".join(args)
    result = not _to_bool(expr)
    ctx.log_event(f"not → {expr.strip()!r} inverted to {str(result).lower()}")
    return "true" if result else "false"