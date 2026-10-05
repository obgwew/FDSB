# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/embed_ops.py

from datetime import datetime as _datetime

import discord

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
