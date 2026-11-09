# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/http_ops.py
# Shared HTTP helpers for $httpGet / $httpPost / $httpPut / $httpPatch / $httpDelete

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import aiohttp
from aiohttp.abc import AbstractResolver

DEFAULT_USER_AGENT = "FDSB-FDScript/1.0 (+https://github.com/obgwew/FDSB)"
MAX_RESPONSE_BYTES = 1 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 15

ALLOW_PRIVATE_NETWORKS = False

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


class BlockedURLError(Exception):
    pass


def _is_forbidden_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    return (
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_multicast or addr.is_reserved or addr.is_unspecified
    )


def assert_valid_scheme(url: str) -> None:
    """Synchronous pre-check: http/https only, a host is present, no obvious local targets."""
    if not url:
        raise BlockedURLError("URL cannot be empty")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedURLError("only http:// and https:// URLs are allowed")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise BlockedURLError("URL has no host")
    if ALLOW_PRIVATE_NETWORKS:
        return
    if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost") or host.endswith(".local"):
        raise BlockedURLError("requests to local addresses are not allowed")
    if _is_forbidden_ip(host):
        raise BlockedURLError("requests to private/local IP addresses are not allowed")


class _SafeResolver(AbstractResolver):
    """Checks the *resolved* IPs at connect time, so DNS tricks and redirects can't reach private hosts."""

    def __init__(self):
        self._inner = aiohttp.ThreadedResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        results = await self._inner.resolve(host, port, family)
        if not ALLOW_PRIVATE_NETWORKS:
            for r in results:
                if _is_forbidden_ip(r["host"]):
                    raise BlockedURLError("host resolves to a private/local IP address")
        return results

    async def close(self):
        await self._inner.close()


_session: aiohttp.ClientSession | None = None
_session_loop: asyncio.AbstractEventLoop | None = None


async def get_session() -> aiohttp.ClientSession:
    """One shared session per event loop (recreated if the loop changed or the session was closed)."""
    global _session, _session_loop
    loop = asyncio.get_running_loop()
    if _session is None or _session.closed or _session_loop is not loop:
        connector = aiohttp.TCPConnector(resolver=_SafeResolver(), limit=20)
        _session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        )
        _session_loop = loop
    return _session


async def read_capped(res: aiohttp.ClientResponse, limit: int = MAX_RESPONSE_BYTES) -> bytes:
    """Read the response body but never more than `limit` bytes."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in res.content.iter_chunked(8192):
        total += len(chunk)
        if total > limit:
            chunks.append(chunk[: max(0, limit - (total - len(chunk)))])
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def close_session() -> None:
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None