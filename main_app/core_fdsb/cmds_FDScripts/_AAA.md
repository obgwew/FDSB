# How to Create a New FDScript Command

This guide explains, step by step, how to add a new `$command` to FDScript. It is written
so that any developer (human or AI) can create a correct, working command **without needing
to read the entire codebase** — just this file, plus one or two existing commands as a
reference (`cmds_FDScripts/*.py`).

FDScript is a small custom scripting language interpreted by `FDCore.py` and `FDScript.py`.
Every `$command` is implemented as its own Python file living in `cmds_FDScripts/`.

---

## 1. The two files every command needs to touch

1. **`cmds_FDScripts/<commandName>.py`** — a new file, one per command. This is where
   you write the actual logic (see §4).
2. **`FDCore.py` → `KNOWN_COMMANDS`** — a big `set[str]` near the top of `FDCore.py`
   (search for `KNOWN_COMMANDS: set[str] = {`). **You must add your command's name to
   this set**, in alphabetical position (the set is grouped with `# a`, `# b`, `# c`
   comment headers). If you skip this step, the tokenizer will treat `$yourCommand` as
   an **unknown command** and it will never reach your file, no matter how correct your
   Python code is.

Optional, only if relevant to your command:

- **`CONTROL_FLOW_COMMANDS`** (also in `FDCore.py`) — only for flow-control keywords
  like `if`/`while`/`for`/`and`/`or`. Normal commands do NOT go here.
- **`_INLINE_WITH_ARGS`** (in `FDCore.py`) — see §5, only needed if your command should
  be usable *inline inside text/other arguments* (e.g. `$sum[1;2]`) rather than only as
  a standalone line.

That's it — there is no manual "registration" step beyond adding the name to
`KNOWN_COMMANDS`. Commands are loaded **dynamically and lazily** via
`importlib.import_module(f"cmds_FDScripts.{name}")` the first time they're used
(see `_load_cmd()` in `FDScript.py`). The filename **must exactly match** the command
name registered in `KNOWN_COMMANDS` (case-sensitive), e.g. `$boostLevel` → `boostLevel.py`.

---

## 2. Anatomy of a command file

Every command module can define up to two functions. Look at `boostCount.py` or
`addButton.py` for real, working examples.

```python
# cmds_FDScripts/myCommand.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error,
)

def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    """Optional. Only needed if the command can be used inline, e.g. $myCommand[...]
    embedded inside a string or another command's argument. Return the resolved
    string, or "" if the command has no meaningful inline value (side-effect only)."""
    ...

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    """Required for any command used as a standalone statement (a line on its own,
    e.g. `$myCommand[a;b]` on its own line in a script). Do the actual work here:
    validate args, talk to Discord, send output, log the event."""
    ...
```

Always import from `FDScript` (not `FDCore`) in command files — `FDScript.py` re-exports
everything you need (`ExecutionContext`, `Command`, the error classes, `_send_error`,
helper functions like `_truncate`, `_extract_all_emojis`, etc.). Some low-level constants
(e.g. `BUTTON_STYLES`) only exist in `FDCore`, so importing directly from `FDCore` is fine
too when `FDScript` doesn't re-export something you need — check both files.

### `execute()` — required for standalone use
Signature: `async def execute(cmd, args, ctx, ch)`
- `cmd` — the `Command` object (`cmd.name`, `cmd.args`, `cmd.raw`, `cmd.line_no`). You
  almost always use the `args` parameter instead of `cmd.args` directly (they're the same
  list, passed separately for convenience).
- `args: list[str]` — the **raw, unresolved** argument strings, split on `;` inside the
  command's `[ ... ]` brackets. E.g. for `$addButton[yes;my_id;Click me;primary]`, `args`
  is `["yes", "my_id", "Click me", "primary"]`. You must call `ctx.resolve(arg)` on each
  one yourself before using it (see §3) — arguments are not pre-resolved for you, because
  some commands need to inspect the raw text first.
- `ctx: ExecutionContext` — the per-execution state object. See §3 for the important
  members.
- `ch: discord.abc.Messageable` — the output destination to send messages/errors to.
  Always obtained via `await ctx.get_dest()` (this is already done for you and passed in).

### `resolve_inline()` — optional, for inline usage
Signature: `def resolve_inline(args, ctx) -> str` (synchronous, **not** `async`!).
This lets your command be evaluated as a *value* inside another string or argument, e.g.
`$var[total;$sum[1;2]]`. If your command has no sensible inline value (it's a pure
side-effect action, like `$ban[...]` or `$addBotReactions[...]`), just return `""` — see
`addButton.py` / `ban.py` for this exact pattern:
```python
def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""
```
**Never** make `resolve_inline` an `async def` — the interpreter calls it synchronously
and will raise a `RuntimeError` at runtime if it detects an async `resolve_inline`
(see `_resolve_inline_cmd()` in `FDScript.py`). If your command genuinely needs to await
something (e.g. a Discord API call) to produce an inline value, it generally should NOT
be inline-only — do the work in `execute()` and send the result instead, or store it via
`ctx.set_var()` for a later `$getVar[]` inline reference.

If you skip `resolve_inline` entirely, your command simply can't be used inline — that's
fine and is the default for most commands (buttons, reactions, moderation actions, etc.).

---

## 3. `ExecutionContext` — what you get and how to use it

`ctx` is created once per script run and threaded through every command. Useful members:

| Member | Type | Purpose |
|---|---|---|
| `ctx.resolve(text: str) -> str` | method | **Always resolve raw args through this** before using them — it expands nested `$commands`, variables, and escape sequences. Never use `args[i]` raw in logic/output. |
| `ctx.message` | `discord.Message` | The triggering message (or a dummy stand-in for event-based triggers). `ctx.message.author`, `.guild`, `.channel` etc. |
| `ctx.interaction` | `discord.Interaction \| None` | Set if triggered by a slash command / component interaction instead of a message. |
| `ctx.bot` | `discord.Client` | The bot instance — use for `ctx.bot.get_user()`, `ctx.bot.fetch_user()`, `ctx.bot.get_guild()`, etc. |
| `await ctx.get_dest()` | coroutine → Messageable | The correct place to `.send()` output (handles interactions, DMs, channel overrides, replies transparently). Usually already given to you as `ch` in `execute()`. |
| `ctx.last_bot_message` | `discord.Message \| None` | The most recent message the bot sent during this script run. Set it after you `.send()` something the user/other commands might reference (e.g. `$addBotReactions` needs this). |
| `ctx.get_embed_builder(index=1)` | method | Returns an `_EmbedBuilder` for embed-related commands (`$author`, `$footer`, `$title`, etc.). Index lets a script build multiple embeds (1–10). |
| `ctx.view` | `discord.ui.View \| None` | The button/select-menu view being built for the next sent message. Create it with `discord.ui.View(timeout=None)` if `None`, then `ctx.view.add_item(...)`. |
| `ctx.set_var(name, value)` / `ctx.get_var(name)` | methods | Script-level temp variables (`temp_vars`) and read-only `builtins` (authorID, guildName, etc.). |
| `ctx.log_event(str)` | method | Appends a line to the execution log shown to the script author (debug/audit trail). **Call this at the end of every successful command** — it's the convention every existing command follows. |
| `ctx.stop_typing()` | method | Stop the "bot is typing…" indicator before sending a final message. |
| `ctx._channel_override` | `discord.abc.Messageable \| None` | Set by `$useChannel`; if present, output should go there instead of the origin channel. See `_resolve_target_message()` pattern in `addBotReactions.py`/`addUserReactions.py` if your command needs to fetch a message that may live in an overridden channel. |

**Argument resolution pattern** used by every command:
```python
value = ctx.resolve(args[0]).strip()
```
For commands that accept free text made of multiple `;`-joined pieces (like emoji lists),
the convention is:
```python
resolved_text = "".join(ctx.resolve(arg) for arg in args)
```

---

## 4. The FDScript error system — how to report problems

There are exactly **four error classes**, all defined in `FDCore.py` and re-exported by
`FDScript.py`. Pick the one that matches the failure:

| Class | When to use it | Icon shown to user |
|---|---|---|
| `FDSyntaxError` | Wrong number/shape of arguments — the script itself is malformed. E.g. "requires at least 4 arguments". | 🔴 |
| `FDLogicError` | Arguments are syntactically fine but semantically invalid at runtime — bad ID, unknown style, duplicate value, not found, etc. This is the most commonly used one. | 🟠 |
| `FDRuntimeError` | An internal/runtime failure unrelated to user input, e.g. division by zero. Rarely needed outside `FDCore.py`'s own math commands. | 🟡 |
| `FDEnvironmentError` | The command *can't* run because of the environment/permissions/context — missing bot permission, wrong context (DM vs guild), rate-limited, etc. | 🔵 |

### How to raise an error
Almost always, **inside `execute()`**, you call the async helper and then `return`:

```python
await _send_error(ch, FDLogicError("`$myCommand` — the ID argument cannot be empty"))
return
```

`_send_error`:
- Sends a formatted message to `ch` (`"{icon} **{category}** — {message}"`), unless
  `ctx.suppress_errors` is set (from `$suppressErrors`), in which case it logs instead
  and optionally sends a custom suppressed-error message.
- Then **always raises `FDAbortScript`**, which stops the rest of the script from
  running. **You must `return` immediately after calling `_send_error`** in your own
  code — do not rely on control flow falling through, and do not wrap it in a broad
  `try/except` that swallows `FDAbortScript`.

Conventions to follow (copy these from existing commands):
- Always prefix the error message with the command name in backtick-dollar form, e.g.
  `` "`$ban` — invalid user ID or mention: ..." ``, so users know which command failed.
- Validate all arguments up front and return early with a specific, actionable message
  (see `addButton.py` for a thorough example — it checks style names, empty fields,
  numeric IDs, URL prefixes, row/column capacity, duplicate IDs, etc., each with its own
  clear `FDLogicError`).
- For expected, non-fatal problems you want to **skip past instead of aborting** the whole
  script (e.g. one bad emoji among several), just call `ctx.log_event("warning: ...")`
  and `continue`/`return None` rather than calling `_send_error` — see how
  `addUserReactions.py` handles unsupported emojis differently from
  `addBotReactions.py` (which is stricter and does call `_send_error`). Decide per-command
  whether partial failure should abort or just warn; document your choice in the error
  text if it aborts.
- If you're inside a helper called from **`resolve_inline`** (synchronous, no `ch`
  available) and need to hard-abort the whole script, use
  `ctx._abort_with_error(FDEnvironmentError("..."))` instead of `_send_error` — see
  `boostLevel.py` for the exact pattern. `_abort_with_error` schedules the error message
  as a background task and raises `FDAbortScript` synchronously, which is safe to call
  from non-async code.
- Never raise a raw Python exception for user-facing problems — the dispatcher will catch
  unexpected exceptions and wrap them in a generic `FDLogicError` (`` `$cmd` raised an
  error: `...` ``), which is far less helpful than a deliberate, specific error.

### Discord API errors
Wrap Discord calls in `try/except` and translate them to FDScript errors:
```python
try:
    await guild.ban(discord.Object(id=target_id), reason="...")
except discord.Forbidden:
    await _send_error(ch, FDEnvironmentError(
        "`$ban` — bot lacks `Ban Members` permission or the target's role is higher than the bot's."
    ))
    return
except discord.HTTPException as e:
    ctx.log_event(f"warning: failed to ban user `{target_id}`: `{e.text}`")
```
`discord.Forbidden` → almost always `FDEnvironmentError` (missing permission).
`discord.NotFound` → almost always `FDLogicError` (bad ID / doesn't exist).
Rate limits (`HTTPException` with `e.status == 429`) → sleep `e.retry_after` and retry
once, as shown in `addBotReactions.py` / `addUserReactions.py`.

---

## 5. Standalone vs. inline commands — which do you need?

- **Standalone only** (most commands: `$ban`, `$addButton`, `$addBotReactions`,
  `$authorID`, …): only implement `execute()`. If it needs a no-op inline stub because
  some other part of the system calls `resolve_inline` speculatively, add
  `def resolve_inline(args, ctx): return ""`.
- **Inline + standalone** (`$authorAvatar`, `$boostCount`, …): implement both. Keep the
  URL/value-computation logic in one small shared helper function so `resolve_inline` and
  `execute` don't diverge (see `authorAvatar.py`'s `_resolve_avatar_url()` helper used by
  both).
- **Inline only** (rare, e.g. pure math/getter commands with no side effects worth logging
  as a standalone statement, like `$boostLevel`): you may skip `execute()` — but note that
  if a script author writes it as a bare standalone line, the dispatcher will show:
  `` `$cmd` has no `execute()` — it may be an inline-only command... ``. That's expected
  and fine for inline-only commands.
- If you want your command usable **inside another argument or string**
  (e.g. `$var[x; $myCommand[1;2] ]`), and it's not naturally control flow, also add its
  name to `_INLINE_WITH_ARGS` in `FDCore.py` (only required for commands whose inline
  form needs its own bracketed args to be parsed specially at the tokenizer level; check
  how similar existing commands — e.g. `sum`, `randomint`, `authorAvatar` — are registered
  there before deciding you need this. Most commands do NOT need to touch this set).

---

## 6. Full worked example

Let's create `$serverName`, a simple command that sends the current guild's name, with
an optional guild-ID argument (mirroring the pattern in `boostCount.py`).

**Step 1 — write `cmds_FDScripts/serverName.py`:**
```python
# cmds_FDScripts/serverName.py
import discord
from FDScript import (
    ExecutionContext, Command,
    FDLogicError, FDEnvironmentError,
    _send_error,
)


def _resolve_guild(ctx: ExecutionContext, guild_id_raw: str | None) -> discord.Guild | None:
    if guild_id_raw:
        if not guild_id_raw.isdigit():
            return None
        return ctx.bot.get_guild(int(guild_id_raw))
    if ctx.message.guild is not None:
        return ctx.message.guild
    return None


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    guild_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else None
    guild = _resolve_guild(ctx, guild_id)
    return guild.name if guild else ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    guild_id = ctx.resolve(args[0]).strip() if args and args[0].strip() else None

    if guild_id is not None and not guild_id.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$serverName` — guild ID must be a numeric snowflake (got `{guild_id}`)"
        ))
        return

    guild = _resolve_guild(ctx, guild_id)
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$serverName` — no guild available in this context "
            "(cannot be used in DMs without a guild ID, or bot isn't in that guild)"
        ))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(guild.name)
    ctx.last_bot_message = sent
    ctx.log_event(f"serverName → {guild.name!r} (guild {guild.id})")
```

**Step 2 — register it in `FDCore.py`:**
Find `KNOWN_COMMANDS` and add `"serverName"` under the `# s` group, alphabetically:
```python
    # s
    "sendEmbedMessage", "sendMessage", "serverOwnerID", "serverName", "setBotStatus", "setVar",
```

That's the entire integration. No other file needs to change.

---

## 7. Checklist — verifying a new command works

Walk through this before considering the command done:

1. **Name match** — the Python filename (`myCommand.py`) exactly matches the string you
   added to `KNOWN_COMMANDS` (case-sensitive), and matches what users will type as
   `$myCommand`.
2. **`KNOWN_COMMANDS` updated** — grep to confirm: it must appear in `FDCore.py`'s
   `KNOWN_COMMANDS` set, otherwise the tokenizer rejects the command before your file is
   ever imported (`Command("__unknown__", [name], line)` → `` Unknown command: `$name` ``).
3. **Imports resolve** — `from FDScript import (...)` must only reference names actually
   re-exported by `FDScript.py` (or import straight from `FDCore` for things like
   `BUTTON_STYLES` that aren't re-exported). A typo here throws at import time and every
   use of the command will fail with the generic "raised an error" wrapper.
4. **`execute()` signature matches exactly**: `async def execute(cmd, args, ctx, ch)`. All
   four positional parameters, `async`.
5. **`resolve_inline()` (if present) is synchronous**, not `async def`, and takes
   `(args, ctx)`.
6. **All args resolved via `ctx.resolve()`** before use — never operate on raw `args[i]`
   strings that might still contain `$var`/`$otherCommand` tokens.
7. **Every failure path sends a specific error and returns** — no silent failures, no bare
   `raise`, no swallowing `FDAbortScript`.
8. **Success path calls `ctx.log_event(...)`** with a short, greppable summary
   (`"commandName → what happened"`), matching the style of neighboring commands.
9. **Discord permission errors are caught** (`discord.Forbidden` → `FDEnvironmentError`)
   rather than bubbling up as an ugly generic exception.
10. **Manual test in a real script**: write a tiny `.fds`/script snippet in a test server
    exercising: (a) the happy path, (b) each validation error you added (missing arg, bad
    ID, wrong type, permission-denied scenario if testable), and (c) — if inline-enabled —
    using it nested inside `$var[x; $myCommand[...] ]` and confirming the returned string
    is correct.
11. **Restart / reload the bot process** if your loader caches modules (dynamic
    `importlib.import_module` calls generally pick up new files on next call without a
    full restart, but confirm with `local_server.py`'s reload behavior in your setup).

Once all eleven boxes are checked, the command is ready for review.