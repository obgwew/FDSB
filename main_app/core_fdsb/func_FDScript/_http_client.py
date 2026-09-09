# cmds_FDScripts/_http_client.py

import aiohttp
import ipaddress
import socket
from urllib.parse import urlparse
from aiohttp.abc import AbstractResolver
from aiohttp.resolver import ThreadedResolver

DEFAULT_USER_AGENT = "FDSB/1.0 (+https://github.com/obgwew/FDSB)"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024

_session: aiohttp.ClientSession | None = None


class BlockedURLError(Exception):
    pass


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


class SafeResolver(AbstractResolver):

    def __init__(self) -> None:
        self._resolver = ThreadedResolver()

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        results = await self._resolver.resolve(host, port, family)

        safe_results = []
        for entry in results:
            ip = entry["host"]
            if _is_blocked_ip(ip):
                continue
            safe_results.append(entry)

        if not safe_results:
            raise BlockedURLError(
                f"Refusing to connect to '{host}': no public IP addresses resolved "
                f"(all resolved IPs were private/internal/blocked)"
            )
        return safe_results

    async def close(self) -> None:
        await self._resolver.close()


def assert_valid_scheme(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedURLError(f"Unsupported scheme: {parsed.scheme or '(none)'}")
    if not parsed.hostname:
        raise BlockedURLError("URL has no host")


async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(
            limit=200,
            limit_per_host=20,
            resolver=SafeResolver(),
            use_dns_cache=True,
            ttl_dns_cache=60,
        )
        _session = aiohttp.ClientSession(
            timeout=REQUEST_TIMEOUT,
            connector=connector,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
    return _session


async def close_session() -> None:
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def read_capped(response: aiohttp.ClientResponse) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_RESPONSE_BYTES:
        raise ValueError(f"Response too large ({content_length} bytes)")

    chunks = bytearray()
    async for chunk in response.content.iter_chunked(65536):
        chunks.extend(chunk)
        if len(chunks) > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeded max allowed size while streaming")
    return bytes(chunks)