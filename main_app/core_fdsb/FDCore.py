# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/FDCore.py 
# FDCore.py — Execution context & shared definitions
# ─────────────────────────────────────────────────────────────

import asyncio
from datetime import datetime as _datetime
import discord
import io
import json
import os
import re
import random
import time

from .engine_FDScript.errors import (
    StopExecution,
    _FDError,
    FDSyntaxError,
    FDLogicError,
    FDRuntimeError,
    FDEnvironmentError,
    FDAbortScript,
    _send_error,
)
from .engine_FDScript.definitions import (
    KNOWN_COMMANDS,
    CONTROL_FLOW_COMMANDS,
    FUNCTION_COMMANDS,
    get_reserved_names,
)
from .engine_FDScript.parse_utils import (
    _find_matching_bracket,
    _check_brackets,
    _ESCAPE_MAP,
    _process_escapes,
    _VALID_TIMESTAMP_FORMATS,
    _build_timestamp,
    _REACTIONS_MAX,
    _CLEAR_DEFAULT,
    _CLEAR_MAX,
    _parse_reaction_emoji,
    _extract_all_emojis,
    _LOG_CHAR_LIMIT,
    _LOG_FILE_LIMIT,
    _truncate,
    _format_uptime,
    _NAMED_COLORS,
    _parse_color,
    _NAMED_SEPARATORS,
    _parse_separator,
    _strip_inline_comment,
    _split_args,
)
from .engine_FDScript.storage_ops import (  # noqa: F401
    set_vars_dir,
    _load_data,
    _save_data,
    _get_ids_data_dir,
    _get_ids_data_path,
    _load_ids_data,
    _save_ids_data,
    _get_user_vars_dir,
    _get_guild_vars_dir,
    _safe_var_filename,
    _load_scoped_var,
    _save_scoped_var,
    _delete_scoped_key,
)
from .engine_FDScript.tokenizer import (  # noqa: F401
    register_command_loader,
    Command,
    TextToken,
    tokenise,
    _CORE_INLINE_NO_ARGS,
    _CORE_INLINE_WITH_ARGS,
    _is_inline_capable,
    tokenise_line,
)
from .engine_FDScript.discord_helpers import (
    _resolve_dm_target,
    _CHANNEL_TYPES,
    _PERMISSION_NAMES,
    _resolve_permission,
)
from .engine_FDScript.runtime_state import (
    set_bot_start_time,
    register_inline_resolver,
)
from .engine_FDScript.prescan_ops import (
    _scan_suppress_errors,
    _REMOVE_LINKS_RE,
    _scan_flag,
    _scan_remove_links,
    _EPHEMERAL_RE,
    _scan_ephemeral,
    script_wants_ephemeral,
)
from .engine_FDScript.links_ops import (
    _MD_LINK_RE,
    _BARE_LINK_RE,
    _strip_links,
    _strip_embed_links,
    _apply_remove_links,
)
from .engine_FDScript.embed_ops import (
    _EmbedAuthor,
    _EmbedBuilder,
)
from .engine_FDScript.channel_wrappers import (
    InteractionChannelWrapper,
    NormalChannelWrapper,
    _ReplyWrapper,
)

def __getattr__(name):
    if name == '_VARS_DIR':
        from .engine_FDScript import storage_ops
        return storage_ops._VARS_DIR
    if name == '_cmd_loader':
        from .engine_FDScript import tokenizer
        return tokenizer._cmd_loader
    if name in ('_BOT_START_TIME', '_inline_resolver'):
        from .engine_FDScript import runtime_state
        return getattr(runtime_state, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

_cooldowns: dict = {}


BUTTON_STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
    "link": discord.ButtonStyle.link
}

class _PendingLog:
    def __init__(self, channel_id: int, name_code: str, entries: list[str]):
        self.channel_id = channel_id
        self.name_code  = name_code
        self.entries    = entries


from .engine_FDScript.math_ops import MathOpsMixin
from .engine_FDScript.resolver_ops import ResolverMixin
from .engine_FDScript.inline_cmds_ops import InlineCmdsMixin

class ExecutionContext(ResolverMixin, InlineCmdsMixin, MathOpsMixin):
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
        self.remove_links: bool = False
        self.ephemeral: bool = False
        self._ephemeral_prepared: bool = False
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
        self.sync_mode: bool = False
        self._sync_tasks: list = []

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

    async def _prepare_ephemeral(self) -> None:
        if self._ephemeral_prepared:
            return
        self._ephemeral_prepared = True
        it = self.interaction
        if it is None:
            return
        try:
            if not it.response.is_done():
                await it.response.defer(ephemeral=True, thinking=True)
                self.log_event("ephemeral → interaction deferred as ephemeral")
            elif it.response.type is discord.InteractionResponseType.deferred_channel_message:
                await it.delete_original_response()
                self.log_event("ephemeral → replaced the public deferred response")
            else:
                self.log_event("ephemeral → interaction already answered; follow-ups will be ephemeral")
        except Exception as e:
            self.log_event(f"warning: could not make the response ephemeral: {e}")

    def strip_links(self, text: str) -> str:
        return _strip_links(text) if (self.remove_links and text) else text

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