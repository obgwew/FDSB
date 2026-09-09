# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/FDCore.py 
# FDScript.py — Interpreter & Public API
# ─────────────────────────────────────────────────────────────

import asyncio
from datetime import datetime as _datetime
import discord
import io
import json
import math
import os
import re
import random
import time

_VARS_DIR: str = ''
_BOT_START_TIME: float = 0.0
_inline_resolver = None 
_cooldowns: dict = {}

BUTTON_STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
    "link": discord.ButtonStyle.link
}

def set_bot_start_time(t: float):
    global _BOT_START_TIME
    _BOT_START_TIME = t

def set_vars_dir(path: str):
    global _VARS_DIR
    _VARS_DIR = path

def register_inline_resolver(fn):
    global _inline_resolver
    _inline_resolver = fn

def _load_data() -> dict:
    if not _VARS_DIR or not os.path.isdir(_VARS_DIR):
        return {}
    result = {}
    for fname in os.listdir(_VARS_DIR):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(_VARS_DIR, fname), 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'name' in data:
                result[data['name']] = data.get('value', '')
        except Exception:
            pass
    return result

def _save_data(data: dict):
    if not _VARS_DIR:
        return
    os.makedirs(_VARS_DIR, exist_ok=True)
    for name, value in data.items():
        safe = ''.join(c for c in name if c.isalnum() or c in ('-', '_')).strip() or 'var'
        path = os.path.join(_VARS_DIR, f'{safe}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'name': name, 'value': str(value)}, f, ensure_ascii=False, indent=2)

def _get_ids_data_dir() -> str:
    if not _VARS_DIR:
        return ''
    return os.path.join(os.path.dirname(_VARS_DIR), 'bot_ids')

def _get_ids_data_path() -> str:
    return os.path.join(_get_ids_data_dir(), 'ids_data.json')

def _load_ids_data() -> dict:
    path = _get_ids_data_path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_ids_data(data: dict):
    path = _get_ids_data_path()
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

KNOWN_COMMANDS: set[str] = {
    # a
    "addBotReactions", "addButton", "addTimestamp", "addUserReactions", "and",
    "author", "authorIcon", "authorID", "authorName", "authorURL",
    "authorAvatar", "authorServerAvatar", "addSelectMenuOption",
    # b
    "ban", "boostCount", "boostLevel", "botID", "botLeave", "botName", "break",
    # c
    "call", "ceil", "changeUsername", "channelExists", "channelID", "channelName",
    "channelType", "charCount", "clear", "clientTyping", "cloneRole",
    "color", "cooldown", "createChannel", "createRole", "cropText", "customID",
    # d
    "deleteChannels", "deletecommand", "deleteRole", "description",
    "displayName", "div", "dm",
    # e
    "editButton", "editChannelPerms", "editIn", "editMessage", "editSplitOut",
    "elif", "else", "endfor", "endfunc", "endif",
    "endwhile", "emojiExists", "emojiName", "editSelectMenu", "editSelectMenuOption",
    # f
    "findChannel", "findRole", "floor", "footer", "footerIcon", "for", "func",
    # g
    "getBotInvent", "getCreationDateTimestamp", "getMessage", "getServerInvite",
    "getSplitOutLength", "getTimestamp", "getUserStatus", "getVar",
    "guildID", "guildName", "guildVerificationLvl",
    # h
    "httpAddHeader", "httpDelete", "httpGet", "httpPatch", "httpPost",
    "httpPut", "httpResult", "httpStatus",
    # i
    "if", "image", "isAdmin", "isBooster", "isBot", "isNSFW",
    "isNumber", "isOwner",
    # j
    "joinSplitOut",
    # k
    "kick",
    # l
    "lastBotMessageID", "lastUserMessageID", "log","lineCount",
    # m
    "math", "membersCount", "mention", "message", "messageID",
    "mod", "mul",
    # n
    "numberSeparator", "numberAbbreviate", "newSelectMenu",
    # o
    "onlyAdmin", "onlyIf", "or",
    # p
    "ping", "power",
    # r
    "randomint", "randomRoleID", "randomRoleMention", "randomstr",
    "randomUserID", "removeButtons", "removeComponent", "removeSplitOutElement",
    "replaceRegex", "replaceText", "reply", "replyIn", "return",
    "returnGetReactions", "returnGuildBansID", "returnGuildChannelsID",
    "returnGuildEmojisID", "returnGuildRolesID", "returnGuildUsersID",
    "roleAssign", "round", "removeAllComponents",
    # s
    "sendEmbedMessage", "sendMessage", "serverOwnerID", "setBotStatus", "setVar",
    "slowmode", "splitIn", "splitOut", "strictArgs", "sub", "sum",
    "suppressErrors", "switch","serverIcon",
    # t
    "timeout", "title", "thumbnail",
    # u
    "unban", "untimeout", "uptime", "useChannel",
    # v
    "var", "voiceUsersLimit",
    # w
    "wait", "while",
}

CONTROL_FLOW_COMMANDS: set[str] = {
    "if", "elif", "else", "endif",
    "while", "endwhile",
    "for", "endfor",
    "break", "return",
    "and", "or",
    "onlyIf", "onlyAdmin", "log",
}

FUNCTION_COMMANDS: set[str] = {
    "func", "endfunc", "call",
}

def get_reserved_names() -> set[str]:
    return KNOWN_COMMANDS

class StopExecution(Exception):
    pass

class _FDError(Exception):
    _category: str = "Error"
    _icon: str = "❌"
    def __init__(self, message: str):
        super().__init__(message)
        self.msg = message

class FDSyntaxError(_FDError):
    _category = "Syntax Error"
    _icon = "🔴"

class FDLogicError(_FDError):
    _category = "Logic Error"
    _icon = "🟠"

class FDRuntimeError(_FDError):
    _category = "Runtime Error"
    _icon = "🟡"

class FDEnvironmentError(_FDError):
    _category = "Environment Error"
    _icon = "🔵"

class FDAbortScript(Exception):
    pass

async def _send_error(ch, error) -> None:
    ctx = getattr(ch, 'ctx', None)
    if ctx is not None and getattr(ctx, 'suppress_errors', False):
        ctx.log_event(f"[suppressed] {error._category}: {error.msg}")
        custom_msg = getattr(ctx, 'suppress_errors_message', None)
        if custom_msg and ch is not None:
            try:
                await ch.send(custom_msg)
            except Exception as e:
                print(f"[FDScript Error Logger] Failed to send suppressed-error message: {e}")
        raise FDAbortScript()

    if ch is not None:
        try:
            await ch.send(f"{error._icon} **{error._category}** — {error.msg}")
        except Exception as e:
            print(f"[FDScript Error Logger] Failed to send error to channel: {e}")
    else:
        print(f"[FDScript Console Error] {error._category}: {error.msg}")
    raise FDAbortScript()

def _find_matching_bracket(text: str, open_pos: int) -> int:
    depth = 0
    i = open_pos
    while i < len(text):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def _check_brackets(text: str) -> tuple[bool, str]:
    depth = 0
    for pos, ch in enumerate(text):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth < 0:
                return False, f"Extra closing `]` at position {pos}"
    if depth > 0:
        return False, f"{'One unclosed' if depth == 1 else f'{depth} unclosed'} opening `[`"
    return True, ""

_ESCAPE_MAP: dict[str, str] = {
    'n':  '\n',
    't':  '\t',
    'r':  '\r',
    '\\': '\\',
    '0':  '\0',
    'a':  '\a',
    'b':  '\b',
    'f':  '\f',
    'v':  '\v',
    "'":  "'",
    '"':  '"',
}

def _process_escapes(text: str) -> str:
    def _replace(m: 're.Match') -> str:
        ch = m.group(1)
        return _ESCAPE_MAP.get(ch, m.group(0))
    return re.sub(r'\\(.)', _replace, text)

_VALID_TIMESTAMP_FORMATS = {'t', 'T', 'd', 'D', 'f', 'F', 'R'}

def _build_timestamp(fmt: str) -> str | _FDError:
    fmt = fmt.strip() if fmt.strip() else 'T'
    if fmt not in _VALID_TIMESTAMP_FORMATS:
        return FDLogicError(
            f"`$addTimestamp` — invalid format `{fmt}`.\n"
            f"Valid formats: `t` `T` `d` `D` `f` `F` `R`"
        )
    return f'<t:{int(time.time())}:{fmt}>'

_REACTIONS_MAX: int = 20
_CLEAR_DEFAULT: int = 10
_CLEAR_MAX:     int = 100

def _parse_reaction_emoji(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    if re.match(r'^<a?:[a-zA-Z0-9_]+:\d+>$', raw):
        return raw
    return raw

def _extract_all_emojis(text: str) -> list[str]:
    custom_emoji_pattern = r'<a?:[a-zA-Z0-9_]+:\d+>'
    emoji_range = (
        r'[\U0001F300-\U0001F5FF'
        r'\U0001F600-\U0001F64F'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA70-\U0001FAFF'
        r'\u2600-\u26FF'
        r'\u2700-\u27BF]'
    )
    single_emoji = f'(?:{emoji_range}|[\U0001F1E6-\U0001F1FF]{{2}}|[0-9#*]\ufe0f?\u20e3)'
    modifier  = r'[\U0001F3FB-\U0001F3FF]?'
    selector  = r'\ufe0f?'
    component = f'{single_emoji}{modifier}{selector}'
    unicode_emoji_pattern = f'{component}(?:\u200d{component})*'
    combined_pattern = f'({custom_emoji_pattern}|{unicode_emoji_pattern})'
    return re.findall(combined_pattern, text)

_LOG_CHAR_LIMIT = 2000
_LOG_FILE_LIMIT = 10 * 1024 * 1024

def _truncate(text: str, limit: int = 40) -> str:
    text = text.replace('\n', ' ')
    return text[:limit] + '…' if len(text) > limit else text

def _format_uptime(seconds: float) -> str:
    total = int(seconds)
    days,    total   = divmod(total, 86400)
    hours,   total   = divmod(total, 3600)
    minutes, secs    = divmod(total, 60)
    parts = []
    if days:    parts.append(f"{days}d")
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return ' '.join(parts)

_NAMED_COLORS: dict[str, int] = {
    "red":0xE74C3C, "green":0x2ECC71, "blue":0x3498DB, "yellow":0xF1C40F,
    "orange":0xE67E22, "purple":0x9B59B6, "pink":0xFF69B4, "white":0xFFFFFF,
    "black":0x000000, "gray":0x95A5A6, "grey":0x95A5A6, "cyan":0x1ABC9C,
    "gold":0xF9A825, "navy":0x2C3E50, "lime":0x27AE60, "brown":0xA0522D,
    "teal":0x008080, "magenta":0xFF00FF, "blurple":0x5865F2, "dark":0x2B2D31,
}

def _parse_color(raw: str) -> int:
    raw = raw.strip().lower()
    if raw in _NAMED_COLORS:
        return _NAMED_COLORS[raw]
    try:
        return int(raw.lstrip("#"), 16)
    except ValueError:
        return 0x2B2D31

def _scan_suppress_errors(script_text: str) -> tuple[bool, str | None]:
    match = re.search(r'\$suppressErrors\b', script_text)
    if not match:
        return False, None

    end = match.end()
    if end < len(script_text) and script_text[end] == '[':
        close = _find_matching_bracket(script_text, end)
        if close != -1:
            custom = script_text[end + 1:close].strip()
            return True, (custom or None)

    return True, None

_NAMED_SEPARATORS: dict[str, str] = {
    "dot": ".", "com": ",", "apo": "'", "sem": ";", "colon": ":",
}

def _parse_separator(raw: str) -> str:
    return _NAMED_SEPARATORS.get(raw.strip(), raw.strip())

class _EmbedAuthor:
    __slots__ = ("name", "url", "icon_url")

    def __init__(self, name: str | None = None, url: str | None = None, icon_url: str | None = None):
        self.name = name
        self.url = url
        self.icon_url = icon_url

class _EmbedBuilder:
    def __init__(self):
        self.title:       str | None = None
        self.description: str | None = None
        self.color:       int | None = None
        self.footer:      str | None = None
        self.footer_icon: str | None = None
        self.image:       str | None = None
        self.thumbnail:   str | None = None
        self.timestamp:   _datetime | None = None
        self.author:      _EmbedAuthor | None = None   # ← إضافة

    def is_set(self) -> bool:
        return any(v is not None for v in (
            self.title, self.description, self.color,
            self.footer, self.footer_icon,
            self.image, self.thumbnail, self.timestamp,
            self.author,
        ))

    def set_author(
        self,
        name: str | None = None,
        url: str | None = None,
        icon_url: str | None = None,
    ) -> None:
        has_content = bool((name and name != "\u200b") or url or icon_url)
        if not has_content:
            self.author = None
            return
        self.author = _EmbedAuthor(name=name, url=url, icon_url=icon_url)

    def build(self) -> discord.Embed:
        e = discord.Embed(
            title=self.title or "",
            description=self.description or "",
            color=self.color if self.color is not None else 0x2B2D31,
        )

        if self.footer:
            if self.footer_icon:
                e.set_footer(text=self.footer, icon_url=self.footer_icon)
            else:
                e.set_footer(text=self.footer)
        elif self.footer_icon:
            e.set_footer(text="\u200b", icon_url=self.footer_icon)

        if self.image:
            e.set_image(url=self.image)

        if self.thumbnail:
            e.set_thumbnail(url=self.thumbnail)

        if self.timestamp:
            e.timestamp = self.timestamp

        if self.author:
            e.set_author(
                name=self.author.name or "\u200b",
                url=self.author.url,
                icon_url=self.author.icon_url,
            )

        return e

async def _resolve_dm_target(
    target_str: str,
    ctx,
    ch: discord.abc.Messageable,
) -> discord.User | discord.Member | None:
    target_str = target_str.strip()
    mention_match = re.match(r'^<@!?(\d+)>$', target_str)
    if mention_match:
        user_id = int(mention_match.group(1))
    elif target_str.isdigit():
        user_id = int(target_str)
    else:
        await _send_error(ch, FDLogicError(
            f"`$dm` — invalid target: `{target_str}`.\n"
            f"Use a user ID or a mention (e.g. `<@123456789>`)."
        ))
        return None

    user = ctx.bot.get_user(user_id)
    if user is None:
        try:
            user = await ctx.bot.fetch_user(user_id)
        except discord.NotFound:
            await _send_error(ch, FDEnvironmentError(
                f"`$dm` — no user found with ID `{user_id}`"
            ))
            return None
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$dm` — failed to fetch user `{user_id}`: `{e.text}`"
            ))
            return None
    return user

_CHANNEL_TYPES: dict[str, type] = {
    "text":     discord.TextChannel,
    "voice":    discord.VoiceChannel,
    "category": discord.CategoryChannel,
    "forum":    discord.ForumChannel,
    "stage":    discord.StageChannel,
    "all":      None,
}

_PERMISSION_NAMES: set[str] = {
    "admin","manage_guild","manage_roles","manage_channels","manage_messages",
    "manage_webhooks","manage_nicknames","manage_emojis","manage_threads",
    "manage_events","kick_members","ban_members","moderate_members",
    "mention_everyone","send_messages","send_tts_messages","embed_links",
    "attach_files","read_message_history","use_external_emojis",
    "use_external_stickers","add_reactions","connect","speak","mute_members",
    "deafen_members","move_members","use_voice_activation","priority_speaker",
    "stream","view_channel","view_audit_log","view_guild_insights",
    "change_nickname","create_instant_invite","request_to_speak",
    "use_application_commands","use_embedded_activities",
}

def _resolve_permission(raw: str) -> discord.Permissions | None | bool:
    raw = raw.strip().lower()
    if not raw or raw == "all":
        return None
    if raw.isdigit():
        return discord.Permissions(int(raw))
    if raw in _PERMISSION_NAMES:
        return discord.Permissions(**{raw: True})
    return False

class _PendingLog:
    def __init__(self, channel_id: int, name_code: str, entries: list[str]):
        self.channel_id = channel_id
        self.name_code  = name_code
        self.entries    = entries

class InteractionChannelWrapper:
    def __init__(self, interaction: discord.Interaction, ctx):
        self._interaction = interaction
        self.ctx = ctx

    async def send(self, *args, **kwargs):
        view = kwargs.pop('view', self.ctx.view)
        msg = await self._interaction.followup.send(*args, view=view, **kwargs)
        self.ctx.last_bot_message = msg
        self.ctx._view_dirty = False
        self.ctx._view_dirty_target = None
        return msg

    def __getattr__(self, name):
        return getattr(self._interaction.channel, name)

class NormalChannelWrapper:
    def __init__(self, channel: discord.abc.Messageable, ctx):
        self._channel = channel
        self.ctx = ctx

    async def send(self, *args, **kwargs):
        view = kwargs.pop('view', self.ctx.view)
        msg = await self._channel.send(*args, view=view, **kwargs)
        self.ctx.last_bot_message = msg
        self.ctx._view_dirty = False
        self.ctx._view_dirty_target = None
        return msg

    def __getattr__(self, name):
        return getattr(self._channel, name)

class _ReplyWrapper:
    def __init__(self, message: discord.Message, ctx):
        self._message = message
        self.ctx = ctx

    async def send(self, *args, **kwargs):
        view = kwargs.pop('view', self.ctx.view)
        msg = await self._message.reply(*args, view=view, **kwargs)
        self.ctx.last_bot_message = msg
        self.ctx._view_dirty = False
        self.ctx._view_dirty_target = None
        return msg

    def __getattr__(self, name):
        return getattr(self._message.channel, name)

class ExecutionContext:
    def __init__(self, message: discord.Message = None, bot: discord.Client = None, member: discord.Member = None, is_event: bool = False, interaction: discord.Interaction = None):
        self.bot = bot
        self.is_event = is_event
        self.interaction = interaction
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._main_loop = None
        self.suppress_errors: bool = False
        self.suppress_errors_message: str | None = None
        self.view = None
        self._view_dirty: bool = False
        self._view_dirty_target: discord.Message | None = None
        self.temp_vars: dict = {}
        self._typing_task: asyncio.Task | None = None
        self.last_bot_message: discord.Message | None = None
        self.execution_log: list[str] = []
        self._log_step: int = 0
        self._pending_logs: list[_PendingLog] = []
        self._last_log_step: int = 0
        self.embed_builders: dict[int, _EmbedBuilder] = {}
        self.return_vars: dict = {}
        self.dm_target: discord.User | discord.Member | None = None
        self._channel_override: discord.abc.Messageable | None = None
        self.current_line_no: int | None = None
        self._resolve_root_text: str = ''
        self.text_buffer = ""
        self._pending_inline_actions = []
        self._inline_call_values: dict[str, str] = {}

        if interaction is not None:
            self.message = interaction.message or message
            self.builtins: dict = {
                "authorID": str(interaction.user.id),
                "authorName": interaction.user.name,
                "botID": str(bot.user.id) if bot.user else "",
                "botName": bot.user.name if bot.user else "",
                "channelID": str(interaction.channel.id) if interaction.channel else "",
                "channelName": interaction.channel.name if interaction.channel else "",
                "guildID": str(interaction.guild.id) if interaction.guild else "DM",
                "guildName": interaction.guild.name if interaction.guild else "DM",
                "mention": interaction.user.mention,
                "customID": str(interaction.data.get("custom_id", "")) if interaction.data else ""
            }
        elif message is not None:
            self.message = message
            self.builtins: dict = {
                "authorID": str(message.author.id),
                "authorName": message.author.name,
                "botID": str(bot.user.id) if bot.user else "",
                "botName": bot.user.name if bot.user else "",
                "channelID": str(message.channel.id),
                "channelName": message.channel.name,
                "guildID": str(message.guild.id) if message.guild else "DM",
                "guildName": message.guild.name if message.guild else "DM",
                "mention": message.author.mention,
                "customID": ""
            }
        elif member is not None:
            guild = member.guild
            channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
            
            class DummyMessage:
                def __init__(self):
                    self.id = 0
                    self.author = member
                    self.channel = channel
                    self.guild = guild
                    self.content = ""
            
            self.message = DummyMessage()
            
            self.builtins: dict = {
                "authorID": str(member.id),
                "authorName": member.name,
                "botID": str(bot.user.id) if bot.user else "",
                "botName": bot.user.name if bot.user else "",
                "channelID": str(channel.id) if channel else "",
                "channelName": channel.name if channel else "",
                "guildID": str(guild.id) if guild else "Unknown Guild",
                "guildName": guild.name if guild else "Unknown Guild",
                "mention": member.mention,
                "customID": ""
            }
        else:
            self.message = None
            self.builtins = {}

    def queue_inline_action(self, coro) -> None:
        self._pending_inline_actions.append(coro)

    def log_event(self, entry: str):
        self._log_step += 1
        self.execution_log.append(f"{self._log_step}. {entry}")
        
    def get_embed_builder(self, index: int = 1) -> _EmbedBuilder:
        index = max(1, min(10, index))
        if index not in self.embed_builders:
            self.embed_builders[index] = _EmbedBuilder()
        return self.embed_builders[index]

    @property
    def embed_builder(self) -> _EmbedBuilder:
        return self.get_embed_builder(1)

    def snapshot_log(self, channel_id: int, name_code: str):
        slice_entries = self.execution_log[self._last_log_step:]
        self._pending_logs.append(_PendingLog(channel_id, name_code, list(slice_entries)))
        self._last_log_step = len(self.execution_log)

    def get_var(self, name: str) -> str:
        name = name.strip()
        if name in self.temp_vars:
            return str(self.temp_vars[name])
        if name in self.builtins:
            return str(self.builtins[name])
        return ""

    def set_var(self, name: str, value: str):
        self.temp_vars[name.strip()] = value

    def start_typing(self, channel: discord.TextChannel):
        async def _keep_typing():
            try:
                async with channel.typing():
                    await asyncio.Future()
            except asyncio.CancelledError:
                pass
        self._typing_task = asyncio.create_task(_keep_typing())

    def stop_typing(self):
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None

    async def get_dest(self) -> discord.abc.Messageable:
        if self.interaction is not None:
            return InteractionChannelWrapper(self.interaction, self)
        if self._channel_override is not None:
            return NormalChannelWrapper(self._channel_override, self)
        if self.dm_target is not None:
            dm = await self.dm_target.create_dm()
            return NormalChannelWrapper(dm, self)
        if getattr(self, 'is_global_reply', False):
            return _ReplyWrapper(self.message, self)
        return NormalChannelWrapper(self.message.channel, self)

    def set_line(self, line_no: int | None):
        self.current_line_no = line_no

    def _abort_with_error(self, err: _FDError, pos: int | None = None):
        line_no = self.current_line_no
        col = None

        if pos is not None:
            root = self._resolve_root_text or ''
            extra_lines = root.count('\n', 0, pos)
            last_nl = root.rfind('\n', 0, pos)
            col = pos - last_nl - 1 if last_nl != -1 else pos
            if line_no is not None:
                line_no = line_no + extra_lines

        loc_parts = []
        if line_no is not None:
            loc_parts.append(f"Line {line_no}")
        if col is not None:
            loc_parts.append(f"Col {col + 1}")
        if loc_parts:
            err.msg = f"[{', '.join(loc_parts)}] {err.msg}"

        self.log_event(f"Aborted: {err.msg}")
        ch = self.message.channel if getattr(self, "message", None) else None

        async def _bg_send():
            try:
                await _send_error(ch, err)
            except FDAbortScript:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_bg_send())
        except RuntimeError:
            print(f"[FDScript Console Error] {err._category}: {err.msg}")

        raise FDAbortScript()

    def resolve(self, text: str) -> str:
        if not text:
            return text
        processed = _process_escapes(text)
        self._resolve_root_text = processed
        resolved = self._resolve_pass(processed, base_offset=0)
        if self._inline_call_values and '\uE000' in resolved:
            for sentinel, value in self._inline_call_values.items():
                if sentinel in resolved:
                    resolved = resolved.replace(sentinel, value)
        return resolved

    def resolve_sync(self, text: str) -> str:
        return self.resolve(text)

    def _resolve_pass(self, text: str, base_offset: int = 0) -> str:
        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            if text[i] != '$':
                result.append(text[i])
                i += 1
                continue

            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1

            cmd_name = text[i + 1:j]
            if not cmd_name:
                result.append('$')
                i += 1
                continue

            if j < n and text[j] == '[':
                bracket_end = _find_matching_bracket(text, j)
                if bracket_end == -1:
                    self._abort_with_error(
                        FDSyntaxError(f"Unclosed bracket in `${cmd_name}[`"),
                        base_offset + i
                    )
                inner_raw = text[j + 1:bracket_end]
                inner = self._resolve_pass(inner_raw, base_offset + j + 1)
                resolved = self._apply_cmd(cmd_name, inner, base_offset + i)
                result.append(resolved)
                i = bracket_end + 1
            else:
                val = self._resolve_bare(cmd_name)
                if val is not None:
                    result.append(val)
                    i = j
                elif cmd_name and (cmd_name[0].isalpha() or cmd_name[0] == '_'):
                    self._abort_with_error(
                        FDSyntaxError(f"Unknown Syntax : `${cmd_name}`"),
                        base_offset + i
                    )
                else:
                    result.append('$')
                    i += 1

        return ''.join(result)

    def _resolve_bare(self, cmd_name: str) -> str | None:
        import time as _time
        if cmd_name == 'messageID':
            return str(self.message.id)
        if cmd_name == 'message':
            full = self.message.content.strip()
            if getattr(self, 'is_event', False):
                return full
            parts = full.split(None, 1)
            return parts[1] if len(parts) > 1 else ""
        if cmd_name == 'randomUserID':
            guild = self.message.guild
            if guild:
                members = [m for m in guild.members if not m.bot]
                if members:
                    return str(random.choice(members).id)
            return ""
        if cmd_name == 'addTimestamp':
            return f'<t:{int(_time.time())}:T>'
        if cmd_name == 'uptime':
            if _BOT_START_TIME == 0.0:
                return ""
            return _format_uptime(_time.time() - _BOT_START_TIME)
        if cmd_name == 'ping':
            return f"{round(self.bot.latency * 1000)}ms"
        if cmd_name == 'return':
            return None
        if cmd_name in self.builtins:
            return str(self.builtins[cmd_name])
        
        if _inline_resolver is not None:
            val = _inline_resolver(cmd_name, [], self)
            if val is not None:
                return val
        return None

    def _apply_cmd(self, cmd_name: str, inner: str, pos: int = 0) -> str:
        _ASYNC_ONLY_COMMANDS = ('httpGet', 'httpPost', 'httpPut', 'httpPatch', 'httpDelete')
        if cmd_name in _ASYNC_ONLY_COMMANDS:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` performs a network request and can only be used as its own "
                    f"standalone line (e.g. `${cmd_name}[...]` on its own line), not nested inside "
                    f"another command's arguments like `$description[...]`. Run it on its own line "
                    f"first, then read the result with `$httpResult[...]`."
                ),
                pos
            )

        if cmd_name == 'var':
            parts = _split_args(inner)
            if len(parts) == 1:
                return self.get_var(parts[0])
            if len(parts) == 2:
                self.set_var(parts[0], parts[1])
                self.log_event(f"var [{parts[0]}] ← {_truncate(parts[1])!r}")
                return ""
            self._abort_with_error(
                FDLogicError("`$var[...]` accepts 1 argument (read) or 2 arguments (write)"),
                pos
            )

        if cmd_name == 'return':
            key = inner.strip()
            if not key:
                self._abort_with_error(FDLogicError("`$return[]` — variable name cannot be empty"), pos)
            if key not in self.return_vars:
                self._abort_with_error(
                    FDRuntimeError(f"`$return[{key}]` — `{key}` has no value stored by any `$returnXxx` command"),
                    pos
                )
            return str(self.return_vars[key])

        if cmd_name in ('sum', 'sub', 'mul', 'div', 'mod'):
            parts = _split_args(inner)

            if len(parts) < 2:
                self._abort_with_error(
                    FDLogicError(f"`${cmd_name}` requires at least 2 arguments (e.g. `${cmd_name}[1; 2; 3]`)"),
                    pos
                )

            try:
                values = [float(p) if p else 0.0 for p in parts]
            except ValueError:
                self._abort_with_error(
                    FDLogicError(
                        f"`${cmd_name}` — Non-numeric value. Cannot perform math operations on text, "
                        f"ensure you are using numbers."
                    ),
                    pos
                )

            if cmd_name == 'sum':
                res = sum(values)
            elif cmd_name == 'mul':
                res = 1.0
                for v in values:
                    res *= v
            elif cmd_name == 'sub':
                res = values[0]
                for v in values[1:]:
                    res -= v
            elif cmd_name == 'div':
                res = values[0]
                for v in values[1:]:
                    if v == 0:
                        self._abort_with_error(FDRuntimeError("Division by zero in math operation"), pos)
                    res /= v
            else:
                res = values[0]
                for v in values[1:]:
                    if v == 0:
                        self._abort_with_error(FDRuntimeError("Division by zero in math operation (mod)"), pos)
                    res %= v

            return str(int(res)) if float(res).is_integer() else str(res)

        if cmd_name in ('floor', 'ceil'):
            parts = _split_args(inner)

            if len(parts) != 1:
                self._abort_with_error(
                    FDLogicError(f"`${cmd_name}` requires exactly 1 argument (e.g. `${cmd_name}[3.7]`)"),
                    pos
                )

            try:
                value = float(parts[0]) if parts[0] else 0.0
            except ValueError:
                self._abort_with_error(
                    FDLogicError(
                        f"`${cmd_name}` — Non-numeric value. Cannot perform math operations on text, "
                        f"ensure you are using numbers."
                    ),
                    pos
                )

            res = math.floor(value) if cmd_name == 'floor' else math.ceil(value)
            return str(res)

        if cmd_name == 'power':
            parts = _split_args(inner)

            if len(parts) != 2:
                self._abort_with_error(
                    FDLogicError("`$power` requires exactly 2 arguments: `$power[base; exponent]`"),
                    pos
                )

            try:
                base = float(parts[0]) if parts[0] else 0.0
                exponent = float(parts[1]) if parts[1] else 0.0
            except ValueError:
                self._abort_with_error(
                    FDLogicError(
                        "`$power` — Non-numeric value. Cannot perform math operations on text, "
                        "ensure you are using numbers."
                    ),
                    pos
                )

            try:
                res = base ** exponent
            except (OverflowError, ZeroDivisionError):
                self._abort_with_error(
                    FDRuntimeError("`$power` — result is too large or mathematically undefined"),
                    pos
                )

            if isinstance(res, complex):
                self._abort_with_error(
                    FDRuntimeError(
                        "`$power` — result is a complex number (negative base with fractional exponent)"
                    ),
                    pos
                )

            return str(int(res)) if float(res).is_integer() else str(res)

        if cmd_name == 'randomint':
            parts = [x.strip() for x in inner.split(';')]
            if len(parts) == 2:
                a = int(float(parts[0])) if parts[0] else 0
                b = int(float(parts[1])) if parts[1] else 0
                return str(random.randint(min(a, b), max(a, b)))
            self._abort_with_error(FDLogicError("`$randomint` requires two arguments: `$randomint[min; max]`"), pos)
        if cmd_name == 'randomstr':
            parts = [p.strip() for p in inner.split(';') if p.strip()]
            return random.choice(parts) if parts else ""
        if cmd_name == 'getVar':
            parts = [x.strip() for x in inner.split(';')]
            if len(parts) == 2:
                name, user_id = parts
                if not name:
                    self._abort_with_error(FDLogicError("`$getVar[]` — variable name cannot be empty"), pos)
                if not user_id:
                    self._abort_with_error(FDLogicError("`$getVar[]` — user ID cannot be empty"), pos)
                data = _load_ids_data()
                return str(data.get(name, {}).get(user_id, ''))
            elif len(parts) == 1:
                key = parts[0]
                if not key:
                    self._abort_with_error(FDLogicError("`$getVar[]` — variable name cannot be empty"), pos)
                data = _load_data()
                return str(data.get(key, ''))
            else:
                self._abort_with_error(
                    FDLogicError(
                        "`$getVar[]` requires 1 or 2 arguments: `$getVar[name]` or `$getVar[name; user_id]`"
                    ),
                    pos
                )
        if _inline_resolver is not None:
            args = _split_args(inner) if inner.strip() else []
            val = _inline_resolver(cmd_name, args, self)
            if val is not None:
                return val
        if cmd_name in KNOWN_COMMANDS:
            self._abort_with_error(
                FDLogicError(
                    f"`${cmd_name}` cannot be used as an inline expression inside another command's arguments"
                ),
                pos
            )
        self._abort_with_error(
            FDLogicError(f"Unknown command: `${cmd_name}`"),
            pos
        )
    
class Command:
    def __init__(self, name: str, args: list[str], raw: str, line_no: int | None = None):
        self.name = name
        self.args = args
        self.raw  = raw
        self.line_no = line_no

class TextToken(str):
    def __new__(cls, value: str, line_no: int | None = None):
        obj = str.__new__(cls, value)
        obj.line_no = line_no
        return obj

def _strip_inline_comment(line: str) -> str:
    depth = 0
    for i, ch in enumerate(line):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        elif ch == '#' and depth == 0:
            return line[:i].rstrip()
    return line

def tokenise(line: str) -> 'Command | str | None':
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    line = _strip_inline_comment(line)
    if not line:
        return None
    if not line.startswith("$"):
        return line

    body = line[1:]
    if body in {"else", "endif", "endwhile", "endfor", "endfunc", "break"}:
        return Command(body, [], line)

    bracket_pos = body.find("[")
    if bracket_pos == -1:
        name = body
        if name not in KNOWN_COMMANDS:
            return Command("__unknown__", [name], line)
        return Command(name, [], line)

    name = body[:bracket_pos].strip()
    if name not in KNOWN_COMMANDS:
        return Command("__unknown__", [name], line)

    rest = body[bracket_pos:]
    valid, err_msg = _check_brackets(rest)
    if not valid:
        raise SyntaxError(f"Bracket error in `{name}`: {err_msg}")

    inner = rest[1:-1]
    args  = _split_args(inner)
    return Command(name, args, line)

def _split_args(inner: str) -> list[str]:
    args = []
    depth = 0
    current = []
    for ch in inner:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif ch == ";" and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append("".join(current).strip())
    return args

_INLINE_VARS: set[str] = {
    'message', 'messageID', 'ping', 'uptime', 'mention',
    'authorID', 'authorName', 'botID', 'botName',
    'channelID', 'channelName', 'guildID', 'guildName',
    'randomUserID', 'customID','boostLevel', "guildVerificationLvl",
}

_INLINE_WITH_ARGS: set[str] = {
    'message', 'var', 'return',
    'getVar',
    'randomint', 'randomstr',
    'sum', 'sub', 'mul', 'div', 'mod',
    'floor', 'ceil', 'power',
    'replaceText', 'cropText',
    'editSplitOut',
    'joinSplitOut',
    'removeSplitOutElement', 'httpAddHeader', 'httpResult',
    'authorAvatar','authorServerAvatar','serverIcon',
    'numberSeparator', 'numberAbbreviate',
}

def tokenise_line(line: str, base_line_no: int = 1) -> list:
    line = line.strip()
    if not line or line.startswith('#'):
        return []
    line = _strip_inline_comment(line)
    if not line:
        return []

    def _line_at(pos: int) -> int:
        return base_line_no + line.count('\n', 0, pos)

    tokens:     list      = []
    text_buf:   list[str] = []
    text_start: int       = 0
    i            = 0
    n            = len(line)
    at_boundary  = True

    def flush_text() -> None:
        nonlocal text_buf, text_start
        chunk = ''.join(text_buf).strip()
        if chunk:
            tokens.append(TextToken(chunk, _line_at(text_start)))
        text_buf = []

    while i < n:
        ch = line[i]

        if ch in (' ', '\t'):
            if not text_buf:
                text_start = i
            text_buf.append(ch)
            at_boundary = True
            i += 1
            continue

        if ch == '$' and at_boundary:
            j = i + 1
            while j < n and (line[j].isalnum() or line[j] == '_'):
                j += 1
            cmd_name = line[i + 1:j]

            is_control = cmd_name in {'else', 'endif', 'endwhile', 'endfor', 'break'}
            is_known   = cmd_name in KNOWN_COMMANDS or is_control

            if cmd_name and is_known:
                if j >= n or line[j] != '[':
                    if cmd_name in _INLINE_VARS:
                        if not text_buf:
                            text_start = i
                        text_buf.append(f'${cmd_name}')
                        i = j
                        at_boundary = False
                        continue
                    flush_text()
                    tokens.append(Command(cmd_name, [], f'${cmd_name}', _line_at(i)))
                    i = j
                    at_boundary = True
                    continue

                bracket_end = _find_matching_bracket(line, j)
                if bracket_end == -1:
                    flush_text()
                    tokens.append(Command(
                        '__syntax_error__',
                        [f'Unclosed bracket in `${cmd_name}`'],
                        f'${cmd_name}[',
                        _line_at(i)
                    ))
                    i = j + 1
                    at_boundary = False
                    continue

                inner = line[j + 1:bracket_end]
                ok, err_msg = _check_brackets(f'[{inner}]')
                if not ok:
                    flush_text()
                    tokens.append(Command(
                        '__syntax_error__',
                        [f'Bracket error in `{cmd_name}`: {err_msg}'],
                        line,
                        _line_at(i)
                    ))
                    i = bracket_end + 1
                    at_boundary = True
                    continue

                if cmd_name in _INLINE_WITH_ARGS:
                    if not text_buf:
                        text_start = i
                    text_buf.append(f'${cmd_name}[{inner}]')
                    i = bracket_end + 1
                    at_boundary = False
                    continue

                flush_text()
                tokens.append(Command(cmd_name, _split_args(inner), f'${cmd_name}[{inner}]', _line_at(i)))
                i = bracket_end + 1
                at_boundary = True
                continue

            if cmd_name and not is_known:
                flush_text()
                tokens.append(Command('__unknown__', [cmd_name], f'${cmd_name}', _line_at(i)))
                i = j
                at_boundary = True
                continue

        if not text_buf:
            text_start = i
        text_buf.append(ch)
        at_boundary = False
        i += 1

    flush_text()
    return tokens