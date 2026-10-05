# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/fd_leaderboard_ops.py

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, NamedTuple

from .errors import FDSyntaxError, FDLogicError, FDEnvironmentError
from .storage_ops import (
    _get_user_vars_dir, _get_guild_vars_dir, _load_scoped_var,
    _load_ids_data, _load_data,
)

if TYPE_CHECKING:
    from FDScript import ExecutionContext


def _syntax_error(message: str) -> Exception:
    return FDSyntaxError(message)


def _logic_error(message: str) -> Exception:
    return FDLogicError(message)


def _env_error(message: str) -> Exception:
    return FDEnvironmentError(message)

VAR_TYPES = ("user", "globaluser", "server")
RETURN_TYPES = ("value", "id", "name")

DEFAULT_LIMIT = 10
MAX_LIMIT = 25
MAX_TEXT_LEN = 2000

DEFAULT_FORMAT = "{rank}. {name} — {value}"
_PLACEHOLDER_RE = re.compile(r"\{(rank|id|name|mention|value)\}")


class Entry(NamedTuple):
    id: str
    raw: str
    num: Decimal


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _raw_values(var_type: str, name: str, guild_id: str) -> dict:
    """Return {id: stored_value} for the requested scope."""
    if var_type == "user":
        out = {}
        for key, val in _load_scoped_var(_get_user_vars_dir(), name).items():
            gid, sep, uid = str(key).partition(":")
            if sep and uid and gid == guild_id:
                out[uid] = val
        return out
    if var_type == "globaluser":
        return dict(_load_ids_data().get(name) or {})
    return dict(_load_scoped_var(_get_guild_vars_dir(), name))


def _to_number(value) -> Decimal | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        num = Decimal(text)
    except InvalidOperation:
        return None
    return num if num.is_finite() else None


def collect_ranked(var_type: str, name: str, sort: str, guild_id: str) -> tuple[list[Entry], int]:
    entries: list[Entry] = []
    skipped = 0
    for id_, val in _raw_values(var_type, name, guild_id).items():
        if val is None or str(val).strip() == "":
            continue
        num = _to_number(val)
        if num is None:
            skipped += 1
            continue
        entries.append(Entry(str(id_), str(val).strip(), num))

    entries.sort(key=lambda e: (len(e.id), e.id))                 
    entries.sort(key=lambda e: e.num, reverse=(sort == "desc"))
    return entries, skipped


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _guild_id(ctx: ExecutionContext) -> str:
    return str(ctx.builtins.get("guildID", "DM"))


def _check_variable(cmd: str, name: str) -> Exception | None:
    if not name:
        return _logic_error(f"`${cmd}` — variable name cannot be empty.")
    if name not in _load_data():
        return _logic_error(
            f"`${cmd}` — no global variable `{name}` exists. "
            f"Define it first (e.g. with `$setVar`)."
        )
    return None


def _check_scope(cmd: str, var_type: str, guild_id: str) -> Exception | None:
    if var_type == "user" and guild_id == "DM":
        return _env_error(
            f"`${cmd}` — per-server user variables cannot be ranked in DMs (no server)."
        )
    return None


def _parse_sort(cmd: str, raw: str) -> tuple[str | None, Exception | None]:
    s = raw.strip().lower()
    if not s:
        return "desc", None
    if s in ("asc", "desc"):
        return s, None
    return None, _logic_error(f"`${cmd}` — sort type must be `asc` or `desc` (got `{raw.strip()}`).")


def _parse_type(cmd: str, raw: str) -> tuple[str | None, Exception | None]:
    t = raw.strip().lower()
    if t in VAR_TYPES:
        return t, None
    return None, _logic_error(
        f"`${cmd}` — variable type must be one of {', '.join(f'`{v}`' for v in VAR_TYPES)} "
        f"(got `{raw.strip()}`)."
    )


def _parse_limit(cmd: str, raw: str) -> tuple[int | None, Exception | None]:
    s = raw.strip()
    if not s:
        return DEFAULT_LIMIT, None
    if not s.isdigit() or int(s) < 1:
        return None, _logic_error(f"`${cmd}` — limit must be a positive whole number (got `{s}`).")
    return min(int(s), MAX_LIMIT), None


def _log_skipped(ctx: ExecutionContext, cmd: str, name: str, skipped: int) -> None:
    if skipped:
        ctx.log_event(f"warning: {cmd} [{name}] ignored {skipped} non-numeric value(s)")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _name_for(ctx: ExecutionContext, var_type: str, id_: str, guild_id: str) -> str:
    """Best-effort display name from the bot's cache; falls back to the raw ID."""
    if not id_.isdigit():
        return id_
    n = int(id_)
    if var_type == "server":
        g = ctx.bot.get_guild(n)
        return g.name if g else id_
    g = ctx.bot.get_guild(int(guild_id)) if guild_id.isdigit() else None
    member = g.get_member(n) if g else None
    if member:
        return member.display_name
    user = ctx.bot.get_user(n)
    return user.display_name if user else id_


def _render(fmt: str, rank: int, entry: Entry, var_type: str,
            ctx: ExecutionContext, guild_id: str) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key == "rank":
            return str(rank)
        if key == "id":
            return entry.id
        if key == "value":
            return entry.raw
        if key == "mention":
            return entry.id if var_type == "server" else f"<@{entry.id}>"
        return _name_for(ctx, var_type, entry.id, guild_id)
    return _PLACEHOLDER_RE.sub(sub, fmt)


def _fit(lines: list[str]) -> str:
    while lines and len("\n".join(lines)) > MAX_TEXT_LEN:
        lines.pop()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API — one function per command family
# ---------------------------------------------------------------------------

def board_text(cmd: str, var_type: str, args: list[str],
               ctx: ExecutionContext) -> tuple[str, Exception | None]:
    if not 1 <= len(args) <= 4:
        return "", _syntax_error(
            f"`${cmd}` takes 1 to 4 arguments: `${cmd}[name; sort; limit; format]` "
            f"(everything after `name` is optional)."
        )
    resolved = [ctx.resolve(a) for a in args]
    name = resolved[0].strip()

    err = _check_variable(cmd, name)
    if err is not None:
        return "", err
    sort, err = _parse_sort(cmd, resolved[1] if len(resolved) > 1 else "")
    if err is not None:
        return "", err
    limit, err = _parse_limit(cmd, resolved[2] if len(resolved) > 2 else "")
    if err is not None:
        return "", err
    fmt = resolved[3] if len(resolved) > 3 and resolved[3].strip() else DEFAULT_FORMAT

    guild_id = _guild_id(ctx)
    err = _check_scope(cmd, var_type, guild_id)
    if err is not None:
        return "", err

    entries, skipped = collect_ranked(var_type, name, sort, guild_id)
    _log_skipped(ctx, cmd, name, skipped)

    lines = [
        _render(fmt, rank, e, var_type, ctx, guild_id)
        for rank, e in enumerate(entries[:limit], start=1)
    ]
    text = _fit(lines)
    ctx.log_event(f"{cmd} [{name}] ({sort}) → {len(lines)} entr{'y' if len(lines) == 1 else 'ies'}")
    return text, None


def board_position(cmd: str, args: list[str],
                   ctx: ExecutionContext) -> tuple[str, Exception | None]:
    if not 3 <= len(args) <= 4:
        return "", _syntax_error(
            f"`${cmd}` takes 3 or 4 arguments: `${cmd}[type; name; sort; id]` (`id` is optional)."
        )
    resolved = [ctx.resolve(a) for a in args]

    var_type, err = _parse_type(cmd, resolved[0])
    if err is not None:
        return "", err
    name = resolved[1].strip()
    err = _check_variable(cmd, name)
    if err is not None:
        return "", err
    sort, err = _parse_sort(cmd, resolved[2])
    if err is not None:
        return "", err

    guild_id = _guild_id(ctx)
    err = _check_scope(cmd, var_type, guild_id)
    if err is not None:
        return "", err

    target = resolved[3].strip() if len(resolved) > 3 else ""
    if not target:
        target = guild_id if var_type == "server" else str(ctx.builtins.get("authorID", ""))

    entries, skipped = collect_ranked(var_type, name, sort, guild_id)
    _log_skipped(ctx, cmd, name, skipped)

    position = next((i for i, e in enumerate(entries, start=1) if e.id == target), 0)
    ctx.log_event(f"{cmd} [{name}] {var_type} {target} ({sort}) → {position}")
    return str(position), None


def board_value(cmd: str, args: list[str],
                ctx: ExecutionContext) -> tuple[str, Exception | None]:
    if not 4 <= len(args) <= 5:
        return "", _syntax_error(
            f"`${cmd}` takes 4 or 5 arguments: `${cmd}[type; name; sort; position; return_type]` "
            f"(`return_type` is optional)."
        )
    resolved = [ctx.resolve(a) for a in args]

    var_type, err = _parse_type(cmd, resolved[0])
    if err is not None:
        return "", err
    name = resolved[1].strip()
    err = _check_variable(cmd, name)
    if err is not None:
        return "", err
    sort, err = _parse_sort(cmd, resolved[2])
    if err is not None:
        return "", err

    pos_raw = resolved[3].strip()
    if not pos_raw.isdigit() or int(pos_raw) < 1:
        return "", _logic_error(f"`${cmd}` — position must be a whole number >= 1 (got `{pos_raw}`).")
    position = int(pos_raw)

    rtype = resolved[4].strip().lower() if len(resolved) > 4 and resolved[4].strip() else "value"
    if rtype not in RETURN_TYPES:
        return "", _logic_error(
            f"`${cmd}` — return type must be one of "
            f"{', '.join(f'`{r}`' for r in RETURN_TYPES)} (got `{rtype}`)."
        )

    guild_id = _guild_id(ctx)
    err = _check_scope(cmd, var_type, guild_id)
    if err is not None:
        return "", err

    entries, skipped = collect_ranked(var_type, name, sort, guild_id)
    _log_skipped(ctx, cmd, name, skipped)

    if position > len(entries):
        ctx.log_event(f"{cmd} [{name}] ({sort}) position {position} → empty (only {len(entries)} ranked)")
        return "", None

    entry = entries[position - 1]
    if rtype == "id":
        result = entry.id
    elif rtype == "name":
        result = _name_for(ctx, var_type, entry.id, guild_id)
    else:
        result = entry.raw
    ctx.log_event(f"{cmd} [{name}] ({sort}) position {position} → {rtype} {result!r}")
    return result, None