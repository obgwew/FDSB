# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/channel_wrappers.py

import discord

from .links_ops import _apply_remove_links

class InteractionChannelWrapper:
    def __init__(self, interaction: discord.Interaction, ctx):
        self._interaction = interaction
        self.ctx = ctx

    async def send(self, *args, **kwargs):
        view = kwargs.pop('view', self.ctx.view)
        args, kwargs, _ok = _apply_remove_links(
            self.ctx, args, kwargs, has_view=bool(view and getattr(view, 'children', None))
        )
        if not _ok:
            return None
        if getattr(self.ctx, 'ephemeral', False):
            await self.ctx._prepare_ephemeral()
            kwargs.setdefault('ephemeral', True)
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
        args, kwargs, _ok = _apply_remove_links(
            self.ctx, args, kwargs, has_view=bool(view and getattr(view, 'children', None))
        )
        if not _ok:
            return None
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
        args, kwargs, _ok = _apply_remove_links(
            self.ctx, args, kwargs, has_view=bool(view and getattr(view, 'children', None))
        )
        if not _ok:
            return None
        msg = await self._message.reply(*args, view=view, **kwargs)
        self.ctx.last_bot_message = msg
        self.ctx._view_dirty = False
        self.ctx._view_dirty_target = None
        return msg

    def __getattr__(self, name):
        return getattr(self._message.channel, name)
