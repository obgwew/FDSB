# cmds_FDScripts/image.py
import re
import discord
from FDScript import ExecutionContext, Command, FDLogicError, _send_error

_URL_RE = re.compile(r"https?://\S+")


def _extract_url_and_flag(args: list[str], ctx: ExecutionContext) -> tuple[str | None, bool, int]:
    if not args:
        return None, False, 1

    remove_embed = False
    index = 1
    url_args = args

    if len(url_args) > 1:
        last_arg = url_args[-1].strip().lower()
        if last_arg in ("yes", "no"):
            remove_embed = (last_arg == "yes")
            url_args = url_args[:-1]

    if not remove_embed and len(url_args) > 1:
        idx_str = ctx.resolve(url_args[-1]).strip()
        if idx_str.isdigit():
            index = int(idx_str)
            url_args = url_args[:-1]

    resolved_text = " ".join(ctx.resolve(arg) for arg in url_args)
    match = _URL_RE.search(resolved_text)
    url = match.group(0).rstrip(").,;!?>\"'") if match else None

    return url, remove_embed, index


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    if args:
        url, remove_embed, index = _extract_url_and_flag(args, ctx)
        if url:
            if remove_embed:
                return url
            else:
                ctx.get_embed_builder(index).image = url
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if not args:
        await _send_error(ch, FDLogicError(
            "`$image` requires at least one argument: $image[url; yes/no (optional); index (optional)]"
        ))
        return

    url, remove_embed, index = _extract_url_and_flag(args, ctx)
    if not url:
        await _send_error(ch, FDLogicError(
            "`$image` — no valid URL found in the given argument(s). "
            "The resolved text must contain a URL starting with http:// or https://"
        ))
        return

    if remove_embed:
        ctx.stop_typing()
        dest = await ctx.get_dest()
        sent = await dest.send(url)
        ctx.last_bot_message = sent
        ctx.log_event(f"image → {url!r} (outside embed)")
    else:
        ctx.get_embed_builder(index).image = url
        ctx.log_event(f"image → {url!r} (embed index {index})")