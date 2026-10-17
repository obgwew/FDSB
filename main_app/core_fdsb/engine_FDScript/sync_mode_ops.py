# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/sync_mode_ops.py

import discord

print(f"[sync_mode_ops] loaded: {__file__} | syncMode single-message build 3")


def _given(value) -> bool:
    return value is not None and value is not discord.utils.MISSING


def sync_add_text(ctx, text: str, line_no: int | None = None) -> None:
    if not text or not text.strip():
        return
    buf = ctx.text_buffer
    if buf and not buf.endswith("\n"):
        same_line = line_no is not None and getattr(ctx, "_last_text_line", None) == line_no
        if same_line:
            buf += "" if buf.endswith((" ", "\t")) else " "
        else:
            buf += "\n"
    ctx.text_buffer = buf + text
    ctx._last_text_line = line_no
    ctx._sync_used = True


def sync_merge_view(ctx, view) -> None:
    if not _given(view) or not getattr(view, "children", None):
        return
    base = ctx._sync_view
    if base is None or base is view:
        ctx._sync_view = view
        return
    for item in list(view.children):
        try:
            view.remove_item(item)
            base.add_item(item)
        except Exception as e:
            ctx.log_event(f"warning: syncMode could not merge a component: {e}")
    ctx._sync_used = True


class _SyncPlaceholder:
    id = 0
    embeds: list = []
    attachments: list = []
    author = None

    def __init__(self, dest, content):
        self.content = content or ""
        self.channel = getattr(dest, "channel", dest)
        self.guild = getattr(self.channel, "guild", None)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        async def _noop(*_a, **_k):
            return self
        return _noop


class _SyncCollector:
    _SILENT = {"ephemeral", "allowed_mentions", "delete_after", "reference",
               "mention_author", "silent", "suppress_embeds", "tts", "wait"}

    def __init__(self, dest, ctx):
        self._dest = dest
        self._ctx = ctx

    def __getattr__(self, name):
        return getattr(self._dest, name)

    async def send(self, content=None, *, embed=None, embeds=None, view=None,
                   file=None, files=None, **kwargs):
        ctx = self._ctx
        if _given(content):
            sync_add_text(ctx, str(content))
        if _given(embed):
            ctx._sync_embeds.append(embed)
        if _given(embeds):
            ctx._sync_embeds.extend(embeds)
        if _given(file):
            ctx._sync_files.append(file)
        if _given(files):
            ctx._sync_files.extend(files)
        sync_merge_view(ctx, view)
        ignored = [k for k in kwargs if k not in self._SILENT]
        if ignored:
            ctx.log_event(f"syncMode → ignored send option(s): {', '.join(ignored)}")
        ctx._sync_used = True
        ctx.log_event("syncMode → added to the single message")
        return _SyncPlaceholder(self._dest, content if _given(content) else "")


class SyncModeMixin:
    _SYNC_TIMERS = ("wait", "replyIn")

    async def _flush_sync_batch(self, ctx) -> None:
        if not ctx._sync_used:
            return
        ctx._sync_flushing = True
        try:
            await self._flush_sync_message(ctx)
        finally:
            ctx._sync_flushing = False

    async def await_sync_tasks(self, ctx) -> None:
        return