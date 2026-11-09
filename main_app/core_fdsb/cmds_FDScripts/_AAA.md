# How to Create a New FDScript Command

This guide explains, step by step, how to add a new `$command` to FDScript. It is written
so that any developer (human or AI) can create a correct, working command **without needing
to read the entire codebase** — just this file, plus one or two existing commands as a
reference (`cmds_FDScripts/*.py`).

FDScript is a small custom scripting language. The interpreter is split into a package of
focused modules (`main_app/core_fdsb/engine_FDScript/`) that `FDScript.py` composes into a
single engine. Every `$command` is implemented as its own Python file living in
`cmds_FDScripts/`.

> **Golden Rule:** every command is a neutral tool that follows its documented purpose and
> syntax exactly — see the *Golden Rule* section below.

> **What changed in this revision:** the old monolithic `FDCore.py` has been split into the
> `engine_FDScript/` modules. `KNOWN_COMMANDS` now lives in `definitions.py`, the error
> classes in `errors.py`, and the inline-detection sets in `tokenizer.py`. New sections cover
> the optional `prefetch()` hook, argument syntax, output delivery (`removeLinks`,
> `$ephemeral`, `syncMode`), return values/storage, and HTTP commands.

---

## Golden Rule — every command is a neutral tool

A command is a **neutral tool**. It does exactly what its documented purpose and syntax say —
nothing more, nothing less. This rule applies to every existing and every new command, and it
overrides any "helpful" instinct to add behavior that was not asked for.

1. **One fixed syntax per command.** The syntax (how many arguments, in which order, and what
   each one means) is defined by the command's purpose. Validate against that syntax exactly.
   A wrong argument count or an invalid value gets a specific error — never guess, reorder,
   default, or silently accept extra/missing arguments.
2. **Never assume a party.** Do not assume the command acts on, or for, the script author, the
   triggering user, the current guild/channel, the bot owner, or any other party. The target is
   whatever the arguments say. A context fallback (e.g. "current guild when the ID is omitted")
   is allowed **only** if that fallback is part of the command's documented syntax.
3. **Follow the intended purpose — no hidden behavior.** No implicit filters, permission gates,
   "who is allowed" policies, limits, extra messages, or side effects beyond what the purpose
   defines. If a filter *is* part of the purpose (e.g. "human members only"), it must be stated
   in the header comment. Access control and safety are the job of the layers that already
   provide them (Discord permissions, the blacklist commands, the libraries the code calls) —
   not something each command re-invents on its own.
4. **Report, don't judge.** Perform the requested action or return the requested data as-is.
   Errors are only for: invalid input, an environment/permission problem, or an empty result
   (following the convention of neighboring commands).
5. **Document the contract in the header comment** of the command file: its exact syntax, what
   it does or returns, the `ctx.return_vars` key it stores (if any), and any filter that is
   part of its purpose.

---

## 0. Engine module map (where things live)

You rarely need to open these, but when something is not behaving, this is where to look.

| Module | Responsibility |
|---|---|
| `definitions.py` | `KNOWN_COMMANDS`, `CONTROL_FLOW_COMMANDS`, `FUNCTION_COMMANDS`, `get_reserved_names()` |
| `tokenizer.py` | Splits a script line into `Command` / `TextToken`; decides which commands are inline-capable (`_CORE_INLINE_*`, `_NEVER_INLINE`, `_is_inline_capable`) |
| `parse_utils.py` | Bracket matching, `_split_args`, comment stripping, escapes (`\n`, `\s`, …), colors, timestamps, `_truncate`, emoji extraction, limits (`_CLEAR_MAX`, …) |
| `resolver_ops.py` | `ctx.resolve()` — expands nested `$cmd[...]`, bare `$name` built-ins |
| `inline_cmds_ops.py` | `_apply_cmd()` — inline dispatch (`$var`, `$return`, `$getVar`, random, math, then your `resolve_inline`) |
| `math_ops.py` | `sum sub mul div mod floor ceil power` |
| `control_flow_ops.py` | `if/elif/else`, `while`, `for`, `break` |
| `functions_ops.py` | `$func` / `$call`, inline `$call[...]` capture, the `prefetch()` pass |
| `errors.py` | The four error classes, `FDAbortScript`, `_send_error` |
| `channel_wrappers.py` | The objects returned by `ctx.get_dest()` (apply `removeLinks`, `$ephemeral`, pending view) |
| `embed_ops.py` | `_EmbedBuilder`, `send_embed_message()`, `flush_pending_message()` |
| `sync_mode_ops.py` | `syncMode` — collects everything into one message |
| `links_ops.py` | `$removeLinks` stripping logic |
| `prescan_ops.py` | Script-wide flags found by regex *before* execution (`$suppressErrors`, `$removeLinks`, `$ephemeral`) |
| `storage_ops.py` | JSON-file storage for global / user / guild variables |
| `fd_leaderboard_ops.py` | Leaderboard commands' shared logic |
| `blacklist_ops.py` | `$blackListUsers/Roles/Server` logic |
| `http_ops.py` | Shared, SSRF-safe HTTP session for `$httpGet/Post/Put/Patch/Delete` |
| `discord_helpers.py` | `_resolve_dm_target`, channel-type map, permission-name resolution |
| `runtime_state.py` | Process-wide state (bot start time, registered inline resolver) |

Engine modules carry the project header (copyright line + `SPDX-License-Identifier:
AGPL-3.0-or-later` + a path comment). Keep it on any new engine module.

---

## 1. The files every command needs to touch

1. **`cmds_FDScripts/<commandName>.py`** — a new file, one per command. This is where
   you write the actual logic (see §2).
2. **`engine_FDScript/definitions.py` → `KNOWN_COMMANDS`** — a big `set[str]` at the top of
   the file (search for `KNOWN_COMMANDS: set[str] = {`). **You must add your command's name
   to this set**, in alphabetical position (the set is grouped with `# a`, `# b`, `# c`
   comment headers). If you skip this step, the tokenizer will treat `$yourCommand` as
   an **unknown command** and it will never reach your file, no matter how correct your
   Python code is.

Optional, only if relevant to your command:

- **`CONTROL_FLOW_COMMANDS`** (also in `definitions.py`) — only for flow-control keywords
  like `if`/`while`/`for`/`and`/`or`. Normal commands do NOT go here.
- **`_NEVER_INLINE`** (in `tokenizer.py`) — commands that must always run as their own
  statement even though their module defines `resolve_inline` (e.g. `wait`, `replyIn`,
  `sendEmbedMessage`, `log`, `addBotReactions`, `addUserReactions`). See §5.
- **`_CORE_INLINE_NO_ARGS` / `_CORE_INLINE_WITH_ARGS`** (in `tokenizer.py`) — only for
  *engine built-ins* that are resolved inside the engine itself (`$var`, `$sum`, …). A
  command in `cmds_FDScripts/` does **not** go here; it becomes inline-capable
  automatically by defining `resolve_inline` (see §5).
- **`_ASYNC_ONLY_COMMANDS`** (in `inline_cmds_ops.py`, inside `_apply_cmd`) — add a
  command here if it performs a network request or any other async work and must never be
  nested inside another command's arguments (this is how `$httpGet` & co. are blocked).
- **`prescan_ops.py`** — only if you are adding a new *script-wide flag* (a command whose
  presence anywhere in the script changes behavior for the whole run, like `$ephemeral`).
  Add a regex + scan function there, following `_scan_ephemeral`.

There is no manual "registration" step beyond adding the name to `KNOWN_COMMANDS`.
Commands are loaded **dynamically and lazily** via
`importlib.import_module(f"cmds_FDScripts.{name}")` the first time they're used
(see `_load_cmd()` in `FDScript.py`; the tokenizer receives it through
`register_command_loader()`). The filename **must exactly match** the command
name registered in `KNOWN_COMMANDS` (case-sensitive), e.g. `$boostLevel` → `boostLevel.py`.

> **Reserved names:** `get_reserved_names()` returns `KNOWN_COMMANDS`. Once your command is
> added, its name is reserved — a user script that already uses that word as a function or
> variable name may start to conflict. Pick names accordingly.

---

## 2. Anatomy of a command file

Every command module can define up to three functions. Look at `boostCount.py` or
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
    string. Synchronous only."""
    ...

async def prefetch(args: list[str], ctx: ExecutionContext, dest) -> None:
    """Optional. Async pre-step for an inline command that needs to await something
    (a Discord fetch, say) before its synchronous resolve_inline runs. See below."""
    ...

async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    """Required for any command used as a standalone statement (a line on its own,
    e.g. `$myCommand[a;b]` on its own line in a script). Do the actual work here:
    validate args, talk to Discord, send output, log the event."""
    ...
```

Always import from `FDScript` (not the engine modules) in command files — `FDScript.py`
re-exports what you normally need (`ExecutionContext`, `Command`, the error classes,
`_send_error`, helpers like `_truncate`, `_extract_all_emojis`, etc.). If something you need
isn't re-exported (e.g. `BUTTON_STYLES`, or helpers from `storage_ops.py`, `http_ops.py`,
`embed_ops.py`), import it straight from its engine module — check both places.

### `execute()` — required for standalone use
Signature: `async def execute(cmd, args, ctx, ch)`
- `cmd` — the `Command` object (`cmd.name`, `cmd.args`, `cmd.raw`, `cmd.line_no`). You
  almost always use the `args` parameter instead of `cmd.args` directly (they're the same
  list, passed separately for convenience).
- `args: list[str]` — the **raw, unresolved** argument strings, split on `;` inside the
  command's `[ ... ]` brackets. E.g. for `$addButton[yes;my_id;Click me;primary]`, `args`
  is `["yes", "my_id", "Click me", "primary"]`. You must call `ctx.resolve(arg)` on each
  one yourself before using it (see §4) — arguments are not pre-resolved for you, because
  some commands need to inspect the raw text first.
- `ctx: ExecutionContext` — the per-execution state object. See §4 for the important
  members.
- `ch: discord.abc.Messageable` — the output destination to send messages/errors to.
  Always obtained via `await ctx.get_dest()` (this is already done for you and passed in).

### `resolve_inline()` — optional, for inline usage
Signature: `def resolve_inline(args, ctx) -> str` (synchronous, **not** `async`!).
This lets your command be evaluated as a *value* inside another string or argument, e.g.
`$var[total;$sum[1;2]]`. It is reached through the engine's inline pipeline
(`ResolverMixin.resolve` → `_apply_cmd` → the registered inline resolver), which means:

- For `$myCommand[a;b]`, `args` is the **already-resolved inner text, split on `;`** into
  a list (nested inline commands have been expanded before your function is called).
- For a bare `$myCommand` (no brackets), `args` is `[]`.
- The return value is inserted into the surrounding text. `""` is a valid value ("nothing").
  Returning `None` means "I don't handle this name" and the engine falls through to its
  *unknown / cannot be used inline* error — so always return a `str`.

**Never** make `resolve_inline` an `async def` — the interpreter calls it synchronously
and will raise a `RuntimeError` at runtime if it detects an async `resolve_inline`
(see `_resolve_inline_cmd()` in `FDScript.py`). If your command needs to await something
to produce an inline value, use `prefetch()` (next section).

If you skip `resolve_inline` entirely, your command simply can't be used inline — that's
fine and is the default for most commands (buttons, reactions, moderation actions, etc.).

### `prefetch()` — optional, async work for inline commands
Signature: `async def prefetch(args, ctx, dest) -> None`.
Some inline values need an `await` (fetching a member, a message, a channel…). The engine
runs every discovered `prefetch()` **before** it resolves the surrounding command or text
(`FunctionsMixin._prefetch_inline_cmds`, called from `_expand_inline_calls`). The pattern:

1. `prefetch()` does the async lookup and stores the result somewhere on `ctx`
   (e.g. a dict attribute you create, keyed by the resolved argument).
2. `resolve_inline()` — synchronous — reads that stored result and returns it.

Details worth knowing:
- `args` passed to `prefetch()` are the **raw, unresolved** inner args (split with
  `_split_args`), so call `ctx.resolve()` on them yourself.
- `dest` is `await ctx.get_dest(raw=True)` — the raw destination, not a wrapper; use it
  for error reporting (`_send_error(dest, ...)`), not for sending user-visible messages.
- Inside loops/conditions it can run again on every evaluation, so make it idempotent
  (or cache per resolved key).
- It is found by scanning argument text for `$name[`; a bare `$name` with no brackets does
  **not** trigger `prefetch()`.

---

## 3. Argument syntax — what your `args` look like

Understanding what the tokenizer already did saves you from re-parsing:

- Args are split on `;` **only at bracket depth 0** (`_split_args`). A `;` inside a nested
  `[...]` belongs to the nested command. Each arg is `.strip()`-ed.
- Empty trailing args are kept: `$cmd[a;]` → `["a", ""]`. Check for empty strings.
- `$cmd[]` gives `args == []`; `$cmd` with no brackets also gives `[]` — treat them the same.
- Brackets must balance; unbalanced input never reaches your command (the tokenizer emits
  a syntax error first).
- Inline comments: `#` at depth 0 starts a comment, so `#` inside `[...]` is safe but a
  bare `#` in plain text is not.
- Escapes are processed during `ctx.resolve()` (`\n`, `\t`, `\s` for a space that survives
  `strip()`, `\\`, …). Raw `args` still contain the backslash forms.
- Reusable helpers in `parse_utils.py`: `_truncate` (log previews), `_parse_color`,
  `_parse_separator`, `_build_timestamp`, `_parse_reaction_emoji`, `_extract_all_emojis`,
  `_format_uptime`, and the limits `_REACTIONS_MAX`, `_CLEAR_DEFAULT`, `_CLEAR_MAX`.
  Prefer them over re-implementing.

---

## 4. `ExecutionContext` — what you get and how to use it

`ctx` is created once per script run and threaded through every command. Useful members:

| Member | Type | Purpose |
|---|---|---|
| `ctx.resolve(text: str) -> str` | method | **Always resolve raw args through this** before using them — it expands nested `$commands`, variables, and escape sequences. Never use `args[i]` raw in logic/output. |
| `ctx.message` | `discord.Message` | The triggering message (or a dummy stand-in for event-based triggers). `ctx.message.author`, `.guild`, `.channel` etc. |
| `ctx.interaction` | `discord.Interaction \| None` | Set if triggered by a slash command / component interaction instead of a message. |
| `ctx.bot` | `discord.Client` | The bot instance — use for `ctx.bot.get_user()`, `ctx.bot.fetch_user()`, `ctx.bot.get_guild()`, etc. |
| `await ctx.get_dest()` | coroutine → Messageable | The correct place to `.send()` output (handles interactions, DMs, channel overrides, replies, `removeLinks`, `$ephemeral`, `syncMode`). Usually already given to you as `ch` in `execute()`. `get_dest(raw=True)` returns the unwrapped destination. |
| `ctx.last_bot_message` | `discord.Message \| None` | The most recent message the bot sent during this script run. The channel wrappers set it for you on every send; set it manually only if you send through some other path. (`$addBotReactions` etc. depend on it.) |
| `ctx.get_embed_builder(index=1)` | method | Returns an `_EmbedBuilder` for embed-related commands (`$author`, `$footer`, `$title`, etc.). Index lets a script build multiple embeds (1–10). Builders live in `ctx.embed_builders` (`{index: builder}`). |
| `ctx.view` | `discord.ui.View \| None` | The button/select-menu view being built for the next sent message. Create it with `discord.ui.View(timeout=None)` if `None`, then `ctx.view.add_item(...)`. |
| `ctx.text_buffer` | `str` | Plain text accumulated by the script and not yet sent. Flushed with the final message (or earlier by timers / `syncMode`). |
| `ctx.set_var(name, value)` / `ctx.get_var(name)` | methods | Script-level temp variables (`temp_vars`). |
| `ctx.builtins` | `dict` | Read-only built-ins such as `authorID`, `guildID` (`"DM"` when there is no guild), `guildName`. Bare `$name` resolves from here. |
| `ctx.return_vars` | `dict` | Values stored by `$returnXxx` commands, read back by the script with `$return[key]`. See §7. |
| `ctx.log_event(str)` | method | Appends a line to the execution log shown to the script author (debug/audit trail). **Call this at the end of every successful command** — it's the convention every existing command follows. |
| `ctx.set_line(line_no)` | method | Records the current script line so errors report `Line N`. Control-flow code calls it; commands usually don't need to. |
| `ctx.stop_typing()` | method | Stop the "bot is typing…" indicator before sending a final message. |
| `ctx.suppress_errors` / `ctx.remove_links` / `ctx.ephemeral` | flags | Script-wide flags set from the prescan. You normally don't read them directly — `_send_error` and the channel wrappers honor them. |
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

## 5. Standalone vs. inline commands — which do you need?

### How the tokenizer decides (read this once)
`tokenizer.tokenise_line()` decides, per `$name` or `$name[...]` occurrence, whether it is a
**statement** (`Command` token, goes to `execute()`) or **part of the surrounding text**
(resolved later through `resolve_inline`). A command is inline-capable when
`_is_inline_capable()` says so:

1. If the name is in `_NEVER_INLINE` → **never** inline (always a statement).
2. If the name is in the engine's core inline sets (`_CORE_INLINE_NO_ARGS` when written
   without brackets, `_CORE_INLINE_WITH_ARGS` when written with them) → inline.
3. Otherwise the loader imports `cmds_FDScripts/<name>.py` and the command is inline-capable
   **if and only if the module defines `resolve_inline`** (`hasattr` check).

Consequences:
- **No `resolve_inline` ⇒ always a statement.** This is the right choice for side-effect
  commands (`$ban`, `$addButton`, `$kick`, reactions, …). Do not add a `return ""` stub
  "just in case" — a stub makes the tokenizer treat the command as text unless you also
  list it in `_NEVER_INLINE`.
- **`resolve_inline` present ⇒ may be swallowed into text.** If you want both behaviors
  but need the statement form to always run `execute()`, add the name to `_NEVER_INLINE`.
- Nothing in `cmds_FDScripts/` needs to be added to `_CORE_INLINE_*`; those sets are for
  built-ins the engine resolves itself.

> **Verify when you add an inline+standalone command:** older versions of this guide
> recommended `def resolve_inline(args, ctx): return ""` stubs on side-effect commands
> (`ban.py`, `addButton.py`). With the current tokenizer a stub is exactly what turns a
> command inline-capable. Before copying that pattern, run a test script with the command
> on its own line and confirm `execute()` is reached (check the execution log for your
> `log_event` line). If it isn't, remove the stub or add the command to `_NEVER_INLINE`.

### Patterns
- **Standalone only** (most commands: `$ban`, `$addButton`, `$addBotReactions`, …): only
  implement `execute()`.
- **Inline + standalone** (`$authorAvatar`, `$boostCount`, …): implement both. Keep the
  value-computation logic in one small shared helper so `resolve_inline` and `execute`
  don't diverge (see `authorAvatar.py`'s `_resolve_avatar_url()`).
  A neat variant, used by `fd_leaderboard_ops.py`: the helper **returns**
  `(value, error)` instead of raising. `execute()` then does
  `await _send_error(ch, err)` and `resolve_inline()` does `ctx._abort_with_error(err)` —
  one validation path, two error channels.
- **Inline only** (rare, e.g. pure getter commands like `$boostLevel`): skip `execute()`.
  If a script author writes it as a bare standalone line, the dispatcher will show:
  `` `$cmd` has no `execute()` — it may be an inline-only command... ``. That's expected.
- **Inline that needs `await`**: add `prefetch()` (see §2); keep `resolve_inline`
  synchronous.
- **Network / long-running work**: never inline. Add the name to `_ASYNC_ONLY_COMMANDS`
  in `inline_cmds_ops.py` so nesting it inside another command's args produces a clear
  error, and have scripts read the outcome from a later `$httpResult`-style command or
  `ctx.return_vars` (see §7).

---

## 6. The FDScript error system — how to report problems

There are exactly **four error classes**, all defined in `engine_FDScript/errors.py` and
re-exported by `FDScript.py`. Pick the one that matches the failure:

| Class | When to use it | Icon shown to user |
|---|---|---|
| `FDSyntaxError` | Wrong number/shape of arguments — the script itself is malformed. E.g. "requires at least 4 arguments". | 🔴 |
| `FDLogicError` | Arguments are syntactically fine but semantically invalid at runtime — bad ID, unknown style, duplicate value, not found, etc. This is the most commonly used one. | 🟠 |
| `FDRuntimeError` | An internal/runtime failure unrelated to user input, e.g. division by zero, call-depth exceeded. Rarely needed in command files. | 🟡 |
| `FDEnvironmentError` | The command *can't* run because of the environment/permissions/context — missing bot permission, wrong context (DM vs guild), rate-limited, etc. | 🔵 |

Two related classes you should know exist but normally don't raise yourself:
`FDAbortScript` (the "stop the script now" signal) and `StopExecution`.

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
  `try/except` that swallows `FDAbortScript`. (If you must catch broad exceptions around a
  block that may call `_send_error`, re-raise it first: `except FDAbortScript: raise` — see
  `enforce_blacklist()` in `blacklist_ops.py`.)
- Finds the script context through `ch.ctx`. The destination from `ctx.get_dest()` has it,
  so `$suppressErrors` works; a bare `discord.abc.Messageable` does not, and suppression
  would be skipped. Always pass the `ch` you were given.

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
  `boostLevel.py` for the exact pattern. It takes an optional second argument `pos` (the
  character offset in the text being resolved, used to report the line). It schedules the
  error message as a background task and raises `FDAbortScript` synchronously, which is
  safe to call from non-async code.
- Never raise a raw Python exception for user-facing problems — the dispatcher will catch
  unexpected exceptions and wrap them in a generic `FDLogicError` (`` `$cmd` raised an
  error: `...` ``), which is far less helpful than a deliberate, specific error — and,
  unlike `FDAbortScript`, the script **continues** with the next command afterwards.

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

## 7. Delivering output correctly

How you send decides whether script-wide features keep working for your command.

- **Send through `ch` / `await ctx.get_dest()`.** The destination is a wrapper
  (`NormalChannelWrapper`, `InteractionChannelWrapper`, `_ReplyWrapper`; or the `syncMode`
  collector) that automatically: attaches the pending `ctx.view`, applies `$removeLinks`
  (and silently skips a message that would be empty after stripping), applies `$ephemeral`
  for interactions, and records `ctx.last_bot_message`. Sending through `ctx.message.channel`
  or `ctx.bot.get_channel(...)` directly bypasses all of that.
- **Embeds to a specific channel:** use `embed_ops.send_embed_message(ctx, target_ch,
  content=..., embed=..., embeds=...)`. It honors `$ephemeral` only when the target is the
  interaction's own channel (controlled by `EPHEMERAL_FOR_OTHER_CHANNELS`).
- **Anything that sleeps** (timers like `$wait` / `$replyIn`): call
  `embed_ops.flush_pending_message(ctx, ch)` first, so text/embeds/buttons written above the
  timer are delivered above it, then reset happens for you.
- **`syncMode`:** when active, `dest.send()` doesn't post — it collects content, embeds,
  files and views into a single message (`_SyncCollector`). Only these send options are
  honored; anything else is logged as ignored. So: don't depend on the `Message` returned
  by `send()` inside `syncMode` (it is a placeholder with `id = 0`), and don't pass options
  that need a real message.
- **`ctx.stop_typing()`** before the final send, as in the examples.
- **Limits:** Discord content is capped at 2000 characters; commands that build long text
  should truncate (see `_fit()` in `fd_leaderboard_ops.py`).

---

## 8. Returning values, storage and HTTP

**Return values.** A command that *computes* something for the script to use later (e.g.
the `returnGuildRolesID` / `returnGetReactions` family) stores it in `ctx.return_vars[key]`
and the script reads it with `$return[key]` (inline). Reading a key nobody stored aborts the
script with a clear `FDRuntimeError`, so choose stable key names and document them in the
command's header comment.

**Script variables.** `$var[name]` / `$var[name;value]` use `ctx.get_var` / `ctx.set_var`
(temporary, per run). Persistent data goes through `storage_ops.py`:

| Scope | Helpers | Stored in |
|---|---|---|
| Global (`$setVar` / `$getVar[name]`) | `_load_data()` / `_save_data()` | one JSON file per variable in the vars dir |
| Per-user global (`$getVar[name;userID]`) | `_load_ids_data()` / `_save_ids_data()` | `bot_ids/ids_data.json` |
| Per-user per-server | `_get_user_vars_dir()`, `_load_scoped_var()`, `_save_scoped_var()`, `_delete_scoped_key()` | `user_vars/<name>.json`, keys are `"<guildID>:<userID>"` |
| Per-server | `_get_guild_vars_dir()` + the same scoped helpers | `guild_vars/<name>.json` |

Notes: file names are derived from the variable name by `_safe_var_filename()` (only
letters, digits, `-`, `_` survive), so names that differ only in other characters map to
the same file. Values are stored as strings. All helpers no-op / return empty when no vars
directory has been configured (`set_vars_dir`).

**HTTP.** Never open your own `aiohttp` session. Use `http_ops`:
`assert_valid_scheme(url)` first (raises `BlockedURLError`), then `await get_session()`,
and read bodies with `read_capped(res)` (1 MB cap, 15 s timeout). The shared session
re-checks resolved IPs at connect time to block private/loopback targets (SSRF); do not
add switches around it. Translate `BlockedURLError` into an `FDEnvironmentError` /
`FDLogicError`, and register the command in `_ASYNC_ONLY_COMMANDS` (§1).

---

## 9. Full worked example

Let's create `$serverName`, a simple command that sends the current guild's name, with
an optional guild-ID argument (mirroring the pattern in `boostCount.py`).

> The engine already has `$guildName`; `$serverName` is used here purely as a small,
> self-contained teaching example. Use a name that isn't in `KNOWN_COMMANDS` for a real
> command.

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
    # In the inline path `args` are already resolved, but resolving again is harmless.
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
    sent = await ch.send(guild.name)      # `ch` is the wrapper: removeLinks / ephemeral / syncMode apply
    ctx.last_bot_message = sent           # (the wrapper already does this; harmless if kept)
    ctx.log_event(f"serverName → {guild.name!r} (guild {guild.id})")
```

Because this module defines `resolve_inline`, the tokenizer will treat `$serverName` as
inline-capable (§5). If you want a bare `$serverName` line to always go through
`execute()`, add `"serverName"` to `_NEVER_INLINE` in `tokenizer.py`.

**Step 2 — register it in `engine_FDScript/definitions.py`:**
Find `KNOWN_COMMANDS` and add `"serverName"` under the `# s` group, alphabetically
(it goes between `"serverLeaderboard"` and `"serverOwnerID"`):
```python
    # s
    "second", "sendEmbedMessage", "sendMessage", "serverIcon", "serverLeaderboard",
    "serverName", "serverOwnerID", "setBotStatus", "setGuildVar", "setUserVar", "setVar",
```

That's the entire integration for a normal command. No other file needs to change (unless
you need one of the optional sets from §1).

---

## 10. Checklist — verifying a new command works

Walk through this before considering the command done:

1. **Name match** — the Python filename (`myCommand.py`) exactly matches the string you
   added to `KNOWN_COMMANDS` (case-sensitive), and matches what users will type as
   `$myCommand`.
2. **`KNOWN_COMMANDS` updated** — grep to confirm: it must appear in
   `engine_FDScript/definitions.py`'s `KNOWN_COMMANDS` set, otherwise the tokenizer rejects
   the command before your file is ever imported (`Command("__unknown__", [name], line)` →
   `` Unknown command: `$name` ``).
3. **Imports resolve** — `from FDScript import (...)` must only reference names actually
   re-exported by `FDScript.py` (or import straight from the engine module, e.g.
   `BUTTON_STYLES`, `storage_ops`, `http_ops`). A typo here throws at import time and every
   use of the command will fail with the generic "raised an error" wrapper.
4. **`execute()` signature matches exactly**: `async def execute(cmd, args, ctx, ch)`. All
   four positional parameters, `async`.
5. **`resolve_inline()` (if present) is synchronous**, not `async def`, takes `(args, ctx)`,
   and always returns a `str` (never `None`).
6. **Inline decision is deliberate** — if the command has side effects, it does *not*
   define `resolve_inline` (or it is listed in `_NEVER_INLINE`); if it awaits anything, the
   async part is in `prefetch()` or the command is in `_ASYNC_ONLY_COMMANDS`.
7. **All args resolved via `ctx.resolve()`** before use — never operate on raw `args[i]`
   strings that might still contain `$var`/`$otherCommand` tokens.
8. **Every failure path sends a specific error and returns** — no silent failures, no bare
   `raise`, no swallowing `FDAbortScript`, and errors are sent through the `ch` you were
   given (so `$suppressErrors` works).
9. **Output goes through `ch` / `ctx.get_dest()`** (or `send_embed_message` /
   `flush_pending_message`), not directly to a raw channel — so `$removeLinks`,
   `$ephemeral` and `syncMode` keep working.
10. **Success path calls `ctx.log_event(...)`** with a short, greppable summary
    (`"commandName → what happened"`), matching the style of neighboring commands.
11. **Discord permission errors are caught** (`discord.Forbidden` → `FDEnvironmentError`)
    rather than bubbling up as an ugly generic exception.
12. **Manual test in a real script**: write a tiny `.fds`/script snippet in a test server
    exercising: (a) the happy path, (b) each validation error you added (missing arg, bad
    ID, wrong type, permission-denied scenario if testable), (c) — if inline-enabled —
    using it nested inside `$var[x; $myCommand[...] ]` and confirming the returned string
    is correct, (d) the command on its own line (confirm `execute()` actually runs), and
    (e) with `$removeLinks` / `$ephemeral` / `$syncMode` / `$suppressErrors` present, if
    your command sends output or can fail.
13. **Restart / reload the bot process** if your loader caches modules (dynamic
    `importlib.import_module` calls generally pick up new files on next call without a
    full restart, but confirm with `server.py`'s reload behavior in your setup).

14. **Neutrality (Golden Rule)** — the command assumes no party, adds no hidden filter, gate,
    limit or side effect, and its argument syntax is validated exactly as designed. Any
    context fallback used is part of the documented syntax.
15. **Contract documented** — the header comment states the exact syntax, the behavior/return
    value, the `return_vars` key (if any), and any purpose-defined filter.

Once all fifteen boxes are checked, the command is ready for review.