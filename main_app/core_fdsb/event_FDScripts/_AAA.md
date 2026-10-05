# event_FDScripts — How Event Scripts Work

This folder is **not** the same thing as `cmds_FDScripts/`.

- `cmds_FDScripts/` = **implementations** of `$commands`. One Python file per command.
- `event_FDScripts/` = **triggers**. One Python file per Discord event that decides *which
  user-authored `.fds` scripts to run*, builds an `ExecutionContext` for them, and hands
  them to the same interpreter used for commands.

Nothing in this folder implements a user-facing `$command`. Every `handle_event()` ends in
`run_script(...)` or `Interpreter(...).run(ctx)`.

---

## 1. The two sides of the system

| Side | Where | What it is |
|---|---|---|
| **Author side** | `<bot_root>/bot_events/*.fds` | Plain text scripts a user writes in the app's editor. First line must be `#PREFIX:$eventName[...]`. |
| **Engine side** | `event_FDScripts/*.py` (this folder) | Reads those files, decides when each one fires, builds the context, runs them. |

`<bot_root>` is the bot folder (`app_data/<bot>/…`). It is resolved by
`PrefixManager.set_bot_dir()` in `server_FDScript/prefix_manager.py:15` — if the folder you
pass is named `bot_files`, the parent is used as root. Then:
- events → `<bot_root>/bot_events/`
- commands → `<bot_root>/bot_commands/`
- `$log` variables → `<bot_root>/bot_vars/`

So the engine-side folder name and the author-side folder name are unrelated. This folder
(`core_fdsb/event_FDScripts/`) contains the *Python*; `<bot_root>/bot_events/` contains the
*scripts the bot loads at runtime*.

---

## 2. The 11 files in this folder

| File | Role |
|---|---|
| `alwaysReply.py` | `$alwaysReply` — runs for every human message. |
| `messageContains.py` | `$messageContains[a;b;c]` — runs if **any** keyword appears. |
| `messageContainsAll.py` | `$messageContainsAll[a;b;c]` — runs only if **all** keywords appear. |
| `onJoined.py` | `$onJoined` — a member joins a server. |
| `onLeave.py` | `$onLeave` — a member leaves a server. |
| `onVoiceJoined.py` | `$onVoiceJoined` — a member joins a voice channel. |
| `onVoiceLeave.py` | `$onVoiceLeave` — a member leaves a voice channel. |
| `onInteraction.py` | `$onInteraction` / `$onInteraction[customID]` — a button or select is pressed. |
| `onBotMessage.py` | `$onBotMessage` / `$onBotMessage[yes]` — another (or this) bot posts. |
| `onBoostServer.py` | `$onBoostServer` — the server gains a boost (Nitro tier message). |
| `onBotOnline.py` | `$onBotOnline[channelID]` — the bot itself connects. |
| `_event_context.py` | Shared helper: builds a `ExecutionContext` from a `discord.Member`. |
| `_event_scan.py` | Shared helper: iterates the events dir, normalises the first line, extracts `[...]` contents. |

The authoritative list of allowed prefixes is `EVENT_PREFIXES` in
`main_app/core_fdsb/Server.py:51`. It is also what the app UI uses to decide whether a
script belongs in `bot_events/` or `bot_commands/` (`commands_view.py:_is_event_prefix`).

---

## 3. Who calls whom

`Server.py` owns every Discord gateway event. Each one looks up matching `.fds` scripts,
then imports the matching handler **lazily inside the event body** (so importing this
folder never costs anything at startup):

```
discord.py
  └─ Server._make_bot()  →  @bot.event on_ready / on_message / on_member_join / …
       ├─ prefix_manager.get_event_scripts(...)          # reads bot_events/*.fds
       ├─ prefix_manager.get_event_scripts_with_arg(...) # same, but keeps the [arg]
       └─ from main_app.core_fdsb.event_FDScripts.<X> import handle_event
            └─ run_script(...)  or  Interpreter(...).run(ctx)
                 └─ FDCore.tokenise_line → cmds_FDScripts/*  (the actual commands)
```

Two lookup styles exist and they are **not** interchangeable:

- `get_event_scripts(name)` → `list[str]` — content only, prefix argument discarded.
  Used by `onJoined`, `onLeave`, `onVoiceJoined`, `onVoiceLeave`, `alwaysReply`,
  `onBoostServer`.
- `get_event_scripts_with_arg(name)` → `list[tuple[str, str | None]]` — keeps the text
  inside `[...]`. Used only by `onBotOnline`, which needs the channel ID.

Both sort by `os.path.getctime()` (falling back to `getmtime`), oldest first. So when
several event scripts fire at once they run sequentially, oldest file first.

---

## 4. The `#PREFIX:` contract

This is the single most important thing to get right.

The **first line** of every `.fds` file in `bot_events/` must be:

```
#PREFIX:$onJoined
#PREFIX:$onJoined[123456789012345678]
```

Rules, and why each exists:

- `#PREFIX:` is matched case-insensitively in `get_event_scripts*`, but the *name* after it
  is upper-cased before comparing — `$onjoined` and `$ONJOINED` both work. The
  `event_FDScripts/*.py` files that scan the dir themselves (`messageContains`,
  `messageContainsAll`, `onBotMessage`, `onInteraction`) lowercase the whole first line and
  compare against a lowercase constant, so those are also case-insensitive.
- Anything after `[` up to the last `]` is the **argument**:
  - `$onInteraction[<customID>]` — only fire for that button.
  - `$onBotMessage[yes]` — also fire on the bot's own messages.
  - `$onBotOnline[<channelID>]` — where to send output.
  - `$messageContains[a;b;c]` — keyword list, split on `;`.
  - `$onJoined[<channelID>]` — output channel (see §6).
- Files whose first line doesn't start with `#PREFIX:` are invisible to events. Empty files
  are skipped. Every read is wrapped in `try/except`, so one unreadable file can't stop the
  others.
- Commands use the same `#PREFIX:` mechanism but **without** the `$` and matched by
  `startswith(prefix)` on the raw message (`get_scripts_by_message`), requiring the
  character after the prefix to be whitespace or end-of-string.

The prefix line is metadata. `run_script` receives the file's **full text including the
`#PREFIX:` line**, and `Interpreter._strip_inline_comment` drops `#`-comments at bracket
depth 0 — so the prefix line is silently ignored during execution.

---

## 5. The two ways a handler runs the script

Most handlers are a two-liner:

```python
await run_script(message, bot, script_text, is_event=True)
```

`run_script` (`FDScript.py:808`) constructs `Interpreter` + `ExecutionContext` for you.

Four handlers need a context they can't get from `run_script`, and build it manually:

```python
interpreter = Interpreter(script_text)
ctx = build_member_context(bot, member, script_text, "$onJoined")
await interpreter.run(ctx)
```

`onJoined.py`, `onLeave.py`, `onVoiceJoined.py`, `onVoiceLeave.py` do this.

### `is_event`, `is_reply`, `interaction`

| Flag | Set by | Effect |
|---|---|---|
| `is_event=True` | all event handlers | Makes `$message` return the **whole** message content instead of stripping the first word (`FDCore.py:880`). |
| `is_reply=True` | `alwaysReply` only | Sets `ctx.is_global_reply`, so output is sent via `ctx.message.reply(...)` — the reply shows the trigger message. |
| `interaction=…` | `onInteraction` only | Output routes through `InteractionChannelWrapper` → `interaction.followup.send`. Also builds builtins from `interaction.user` / `interaction.data['custom_id']`. |

`onBotOnline` passes `ctx_source=None` when the `[channelID]` lookup fails. `ExecutionContext`
tolerates `message=None` (`builtins = {}`), but `Interpreter._flush_message` will then throw
on `await ctx.get_dest()` → `self.message.channel`, caught by the generic handler in
`Server._make_bot`'s `except Exception: pass`. Prefer a reachable channel ID.

---

## 6. `_event_context.py` — the member-event context

```python
class _EventMessage:          # a fake discord.Message
    channel = None            # filled in later from the prefix's [channelID]
    guild   = member.guild
    author  = member          # so $authorID, $authorName, $mention all work
    content = ""
```

`build_member_context()`:

1. Wraps the member in `_EventMessage`.
2. Builds `ExecutionContext(message=fake_message, bot=bot, member=member)`. Because
   `member` is passed, `ExecutionContext.__init__` takes its **third** branch
   (`FDCore.py:681`) and pre-fills `builtins`: `authorID`, `authorName`, `botID`, `botName`,
   `channelID`, `channelName`, `guildID`, `guildName`, `mention`, `customID`.
3. Searches the **first line** for `\[(\d+)\]` and, if found, sets
   `ctx.message.channel = bot.get_channel(id)`.
4. If the channel isn't found it only `print()`s. `ctx.message.channel` stays `None`, and
   any output send will fail inside the swallowed `except Exception: pass` in `Server.py`.

Consequences for authors: in a `$onJoined` script, `$authorID`/`$authorName`/`$mention`
resolve to the joining member and `ctx.message.guild` is real, but `$message` is empty
(`content = ""`). Always give member events a `[channelID]`, otherwise there is nowhere to
send. `voice_channel` is passed to the handler but **discarded** — `onVoiceJoined` and
`onVoiceLeave` behave identically to `onJoined`/`onLeave` apart from the label used in
error messages. There is no `$voiceChannel` builtin.

---

## 7. `_event_scan.py` — the dir scanner

Used by the four handlers that filter by argument rather than by an exact prefix match.

```python
iter_event_files(events_dir)   # yields (fname, script_text, first_line_normalised)
extract_bracket_content(line)  # text between the first '[' and the last ']'
extract_words(line)            # that text split on ';' with blanks dropped
```

`first_line_norm` is `line.strip().replace(" ", "").lower()`. Note it only strips literal
spaces — a tab in the prefix line will break matching, since the per-handler constants are
plain lowercase strings like `"#prefix:$messagecontains["`.

`extract_words` returns `[]` for an empty bracket, and every caller treats that as
"no match" and skips the file.

---

## 8. Handler-by-handler reference

### `alwaysReply` — `$alwaysReply`
`on_message` → `get_event_scripts("$alwaysReply")` → for each:
`run_script(message, bot, script, is_event=True, is_reply=True)`. Output is a **reply** to
the triggering message. No argument support. Runs for human messages only (bot messages
return earlier).

### `messageContains` — `$messageContains[a;b;c]`
Constant `_PREFIX = "#prefix:$messagecontains["` (with the bracket, so the file must use the
bracket form). Fires if `any(word in message.content.lower())`. Note it lowercases the
message and compares against `extract_words` output, which is **not** lowercased — so
keywords must be written in lowercase to ever match.

### `messageContainsAll` — `$messageContainsAll[a;b;c]`
Same as above but `_PREFIX = "#prefix:$messagecontainsall"` (no bracket in the constant, so
both `$messageContainsAll` and `$messageContainsAll[...]` are accepted) and requires
`all(...)`.

### `onJoined` / `onLeave`
`on_member_join` / `on_member_remove` → `get_event_scripts(...)` → `build_member_context` →
`Interpreter.run`. Both return early if no scripts matched, so the handler module is only
imported when needed.

### `onVoiceJoined` / `onVoiceLeave`
`on_voice_state_update` compares `before.channel` vs `after.channel`. It fires **leave
first, then join**, and only when the channel actually changed — so a mute/unmute or
deafen toggle does not trigger either. Both handlers are given the voice channel but ignore
it.

### `onInteraction` — `$onInteraction` / `$onInteraction[customID]`
Triggered from `on_interaction` for `InteractionType.component` only (slash commands are
ignored). `Server` defers the interaction first, then passes `custom_id` down.

- First line exactly `#prefix:$oninteraction` → fires for **every** component.
- First line `#prefix:$oninteraction[<id>]` → fires only when `extract_bracket_content(...)`
  equals `custom_id.lower()`. The custom ID is lower-cased for comparison but the ID stored
  in the prefix is **not**, so write it lowercase.
- `_schedule()` uses `asyncio.create_task`, so all matching scripts run **concurrently**,
  not sequentially. Each gets `message=interaction.message`, `is_event=True`,
  `is_reply=False`, and the `interaction` itself.
- Deferred + `followup` means output appears after the "thinking…" state; there's no way to
  edit the original message back.

### `onBotMessage` — `$onBotMessage` / `$onBotMessage[yes]`
Fired from `on_message` **before** the human-message path, and `on_message` returns right
after — bot messages never trigger commands or `$alwaysReply`.

- If the author is *this* bot, the script only runs when the argument is exactly `yes`
  (anything else, including a missing argument, is treated as `no`).
- Otherwise any other bot's message runs it.
- `run_script(..., is_event=True)`, `is_reply=False` → plain `send`.

### `onBoostServer` — `$onBoostServer`
`on_message` checks `message.type in _BOOST_MESSAGE_TYPES`
(`premium_guild_subscription`, `_tier_1/2/3`) and returns immediately after — a boost
message is not treated as a command trigger. `is_event=True`.

### `onBotOnline` — `$onBotOnline[channelID]`
Fired from `on_ready`. Uses `get_event_scripts_with_arg`, so the `[channelID]` is preserved.
The channel is resolved with `get_channel`, falling back to `fetch_channel`. The bot's own
status / FGS notification is set up *before* the scripts run. Each script is wrapped in its
own `try/except Exception: pass`, so one failure never blocks the others.

---

## 9. Ordering inside `on_message`

This ordering is fixed and worth knowing when events and commands coexist:

1. boost message? → run `$onBoostServer`, **return**.
2. `message.author.bot`? → run `$onBotMessage`, **return**.
3. `set_fgs_state(STATE_SYNCING)`; run `$alwaysReply`.
4. run `$messageContains`, then `$messageContainsAll`.
5. `get_scripts_by_message(...)` — if any command script matches, run them all
   oldest-first and **return** (`bot.process_commands` is skipped).
6. otherwise `await bot.process_commands(message)`.

So `$alwaysReply` / `$messageContains*` fire even for messages that also trigger a command,
and event handlers never see bot-authored messages.

---

## 10. Error handling — everything is swallowed

Every handler is invoked from a `try/except Exception: pass` or `except Exception: pass` in
`Server.py`. Consequences:

- A crash inside an event script is **invisible** in the Discord channel. `Interpreter.run`
  already catches `FDAbortScript` and generic `Exception` and writes them to the execution log
  (`ctx.log_event`), so the only trace is `ctx.execution_log` — which is discarded unless the
  script used `$log`.
- `set_fgs_state(STATE_SYNCING)` is set but never reset by the handlers; `set_fgs_state(
  STATE_WORKING)` happens on `on_ready`/`on_resumed`.
- `$suppressErrors` works normally inside event scripts: `_send_error` honours
  `ctx.suppress_errors` and still raises `FDAbortScript`, so the script still aborts.
- Import failures are hidden too — the `from … import handle_event` is inside the event body
  under a bare `except`, so a syntax error in this folder looks like "the event simply never
  fires".

---

## 11. Adding a new event

1. **Add the prefix to `EVENT_PREFIXES`** in `main_app/core_fdsb/Server.py:51`. Without this
   the app UI writes the file into `bot_commands/` instead of `bot_events/`
   (`commands_view.py:_is_event_prefix`), and the runtime lookup never matches.
2. **Add the Discord gateway handler** to `_make_bot()` in `Server.py`. Pick the matching
   lookup: `get_event_scripts("$yourEvent")` if the script takes no argument, or
   `get_event_scripts_with_arg("$yourEvent")` if you need the `[...]` text.
3. **Create `event_FDScripts/onYourEvent.py`** exporting `async def handle_event(...)`. Keep
   the name consistent with the prefix.
4. Decide how the context is built:
   - message-shaped trigger → `await run_script(message, bot, script_text, is_event=True)`
     (add `is_reply=True` if the output should be a reply).
   - member-shaped trigger → `Interpreter(script_text)` +
     `build_member_context(bot, member, script_text, "$onYourEvent")`.
   - component trigger → pass `interaction=interaction` so output routes to `followup`.
5. If the event is **directory-scanned** (keyword / custom-ID matching) rather than looked up
   by exact prefix name, also use `_event_scan.iter_event_files` and a lowercase
   `_PREFIX` constant, and call `handle_event(bot_or_message, ..., prefix_manager._bot_events_dir)`.
6. Wrap the call site in `try/except Exception: pass`, import the handler **inside** the
   event body, and `return` early from `on_message` if the event consumes the message.
7. Mirror `onJoined.py` / `onVoiceJoined.py` for the `set_fgs_state(STATE_SYNCING)` call —
   import it locally: `from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING`
   (a module-level import would be circular).
8. Add a wiki entry: `wiki/<lang>/functions/<name>.txt` and register the filename in
   `wiki/<lang>/index.json` for each of the ten languages (`ar ch de en fa fr pl ru tr ur`).
   `wiki_view.py` reads these from GitHub raw at runtime.

### Minimal template (member-shaped)

```python
# main_app/core_fdsb/event_FDScripts/onYourEvent.py
import discord
from main_app.core_fdsb.FDScript import Interpreter
from main_app.core_fdsb.event_FDScripts._event_context import build_member_context


async def handle_event(member: discord.Member, bot: discord.Client, script_text: str):
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)

    interpreter = Interpreter(script_text)
    ctx = build_member_context(bot, member, script_text, "$onYourEvent")
    await interpreter.run(ctx)
```

### Minimal template (message-shaped)

```python
# main_app/core_fdsb/event_FDScripts/onYourEvent.py
import discord
from main_app.core_fdsb.FDScript import run_script


async def handle_event(message: discord.Message, bot: discord.Client, script_text: str):
    from main_app.core_fdsb.Server import set_fgs_state, STATE_SYNCING
    set_fgs_state(STATE_SYNCING)
    try:
        await run_script(message, bot, script_text, is_event=True)
    except Exception as e:
        print(f"[onYourEvent Event Error] : {e}")
```

---

## 12. Checklist

1. Prefix added to `EVENT_PREFIXES` **and** matched by the lookup you chose.
2. `handle_event` is `async` and named exactly `handle_event`.
3. `run_script` / `Interpreter.run` actually invoked (an `async def` that forgets to run the
   script is a silent no-op).
4. `is_event=True` for every event — without it `$message` silently strips its first word.
5. `is_reply=True` only for `alwaysReply`-style reply behaviour.
6. `interaction=…` passed for component events so output reaches the user.
7. Member events get a `[channelID]` in the prefix line, otherwise `ctx.message.channel` is
   `None` and output is dropped.
8. `set_fgs_state` imported **inside** the function (circular-import safe).
9. Call site wrapped in `try/except` and imports kept local.
10. Ordering vs. steps 1–6 of §9 is what you intend.
11. Wiki `.txt` + `index.json` added for all ten languages.
12. Manually test the happy path **and** a trigger that must *not* fire (wrong keyword,
    wrong custom ID, non-boost message, voice state change with the same channel).
