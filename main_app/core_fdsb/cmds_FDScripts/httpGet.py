# cmds_FDScripts/httpGet.py
import json
import discord
import aiohttp
from FDScript import ExecutionContext, Command, FDSyntaxError
from func_FDScript._http_client import get_session, assert_valid_scheme, read_capped, BlockedURLError, DEFAULT_USER_AGENT


async def _process(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 1:
        ctx._abort_with_error(FDSyntaxError("`$httpGet` requires 1 arg: `$httpGet[URL]`"))

    url = (ctx.resolve(args[0])).strip()
    headers = dict(getattr(ctx, "http_headers", {}))
    headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

    try:
        assert_valid_scheme(url)
        session = await get_session()
        async with session.get(url, headers=headers) as res:
            ctx.http_status = res.status
            raw = await read_capped(res)
            try:
                ctx.http_result = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                ctx.http_result = raw.decode("utf-8", errors="replace")
    except BlockedURLError as e:
        ctx.http_status = 400
        ctx.http_result = f"Blocked URL: {e}"
    except (aiohttp.ClientError, TimeoutError) as e:
        ctx.http_status = 500
        ctx.http_result = str(e)
    except Exception as e:
        ctx.http_status = 500
        ctx.http_result = str(e)

    ctx.http_headers = {}
    return ""


async def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return await _process(args, ctx)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    await _process(args, ctx)