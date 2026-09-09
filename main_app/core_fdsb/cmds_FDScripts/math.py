# cmds_FDScripts/math.py
import ast
import math as _math
import operator
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error


_OPERATORS = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod:      operator.mod,
    ast.Pow:      operator.pow,
    ast.USub:     operator.neg,
    ast.UAdd:     operator.pos,
}

_FUNCTIONS = {
    "sqrt":  _math.sqrt,
    "abs":   abs,
    "ceil":  _math.ceil,
    "floor": _math.floor,
    "round": round,
    "log":   _math.log,
    "log2":  _math.log2,
    "log10": _math.log10,
    "sin":   _math.sin,
    "cos":   _math.cos,
    "tan":   _math.tan,
}

_CONSTANTS = {
    "pi":  _math.pi,
    "e":   _math.e,
    "inf": _math.inf,
}


def _eval_node(node: ast.AST) -> float:
    match node:
        case ast.Constant(value=v) if isinstance(v, (int, float)):
            return v

        case ast.Name(id=name) if name in _CONSTANTS:
            return _CONSTANTS[name]

        case ast.BinOp(left=left, op=op, right=right) if type(op) in _OPERATORS:
            l = _eval_node(left)
            r = _eval_node(right)
            if isinstance(op, ast.Pow) and abs(l) > 1e6:
                raise ValueError("exponent too large")
            return _OPERATORS[type(op)](l, r)

        case ast.UnaryOp(op=op, operand=operand) if type(op) in _OPERATORS:
            return _OPERATORS[type(op)](_eval_node(operand))

        case ast.Call(func=ast.Name(id=name), args=call_args, keywords=[]) if name in _FUNCTIONS:
            evaluated = [_eval_node(a) for a in call_args]
            return _FUNCTIONS[name](*evaluated)

        case _:
            raise ValueError(f"unsupported expression: {ast.dump(node)}")


def _safe_eval(expr: str) -> str:
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise ValueError(f"invalid math expression: `{expr}`")

    result = _eval_node(tree.body)

    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if not args:
        return ""
    expr = ctx.resolve(args[0])
    try:
        return _safe_eval(expr)
    except Exception:
        return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$math` requires an expression: `$math[2 + 2]`"
        ))
        return

    expr = ctx.resolve(args[0])

    try:
        result = _safe_eval(expr)
    except ZeroDivisionError:
        await _send_error(ch, FDLogicError(
            "`$math` — division by zero"
        ))
        return
    except ValueError as e:
        await _send_error(ch, FDLogicError(
            f"`$math` — {e}"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(result)
    ctx.last_bot_message = sent
    ctx.log_event(f"math → {expr} = {result}")