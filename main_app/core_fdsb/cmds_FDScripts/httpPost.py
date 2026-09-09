# cmds_FDScripts/httpPost.py
import json
import discord
import aiohttp
from FDScript import ExecutionContext, Command, FDSyntaxError
from func_FDScript._http_client import get_session, assert_valid_scheme, read_capped, BlockedURLError, DEFAULT_USER_AGENT


async def _process(args: list[str], ctx: ExecutionContext) -> str:
    if len(args) < 1:
        ctx._abort_with_error(FDSyntaxError("`$httpPost` requires at least 1 arg: `$httpPost[URL;(Body)]`"))

    url = (await ctx.resolve(args[0])).strip()
    body_raw = (await ctx.resolve(args[1])) if len(args) > 1 else None
    headers = dict(getattr(ctx, "http_headers", {}))
    headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

    json_data = None
    data = None
    if body_raw:
        try:
            json_data = json.loads(body_raw)
        except Exception:
            data = body_raw

    try:
        assert_valid_scheme(url)
        session = await get_session()
        async with session.post(url, headers=headers, json=json_data, data=data) as res:
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