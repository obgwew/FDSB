# cmds_FDScripts/footerIcon.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_URL_RE = re.compile(r"https?://\S+")


def _extract_url_and_index(args: list[str], ctx: ExecutionContext) -> tuple[str | None, int]:
    if not args:
        return None, 1

    resolved_args = [ctx.resolve(a) for a in args]
    index = 1

    if len(resolved_args) > 1 and resolved_args[-1].strip().isdigit():
        index = int(resolved_args[-1].strip())
        resolved_args = resolved_args[:-1]

    resolved_text = " ".join(resolved_args)
    match = _URL_RE.search(resolved_text)
    url = match.group(0).rstrip(").,;!?>\"'") if match else None

    return url, index


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        url, index = _extract_url_and_index(args, ctx)
        if url:
            ctx.get_embed_builder(index).footer_icon = url
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$footerIcon` requires at least one argument: $footerIcon[url;index (optional)]"
        ))
        return

    url, index = _extract_url_and_index(args, ctx)
    if not url:
        await _send_error(ch, FDLogicError(
            "`$footerIcon` — no valid URL found in the given argument(s). "
            "The resolved text must contain a URL starting with http:// or https://"
        ))
        return

    ctx.get_embed_builder(index).footer_icon = url
    ctx.log_event(f"footerIcon → {url!r} (index {index})")