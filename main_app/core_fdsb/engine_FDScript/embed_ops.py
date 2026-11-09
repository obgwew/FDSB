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


# ─────────────────────────────────────────────────────────────
#  Delivery — the ONE entry point for any command that posts an
#  embed to a specific channel (sendEmbedMessage and future ones).
# ─────────────────────────────────────────────────────────────

EPHEMERAL_FOR_OTHER_CHANNELS: bool = False


def _same_channel(interaction, target_ch) -> bool:
    cid = getattr(interaction, "channel_id", None)
    if cid is None:
        cid = getattr(getattr(interaction, "channel", None), "id", None)
    return cid is not None and cid == getattr(target_ch, "id", None)


async def send_embed_message(ctx, target_ch, *, content=None, embed=None, embeds=None):
    kwargs = {}
    if content:
        kwargs["content"] = content
    if embed is not None:
        kwargs["embed"] = embed
    if embeds:
        kwargs["embeds"] = embeds

    hidden = bool(getattr(ctx, "ephemeral", False)) and ctx.interaction is not None
    if hidden and (EPHEMERAL_FOR_OTHER_CHANNELS or _same_channel(ctx.interaction, target_ch)):
        dest = await ctx.get_dest(raw=True)
        kwargs["view"] = discord.utils.MISSING
        sent = await dest.send(**kwargs)
        ctx.log_event("ephemeral → embed message delivered privately to the user")
        return sent

    if hidden:
        ctx.log_event("ephemeral → not applied: the embed targets a different channel")
    return await target_ch.send(**kwargs)


# ─────────────────────────────────────────────────────────────
#  Timers ($wait / $replyIn) — send what the script has built so
#  far BEFORE sleeping, so commands written above a timer are
#  delivered above it.
# ─────────────────────────────────────────────────────────────

async def flush_pending_message(ctx, ch) -> bool:
    text = ctx.strip_links(getattr(ctx, "text_buffer", "") or "").strip()
    embeds = [
        builder.build()
        for _, builder in sorted(ctx.embed_builders.items())
        if builder.is_set()
    ]
    view = ctx.view if (ctx.view and ctx.view.children) else None

    if not text and not embeds and view is None:
        ctx.text_buffer = ""
        return False

    kwargs = {}
    if text:
        kwargs["content"] = text
    if embeds:
        kwargs["embeds"] = embeds
    if view is not None:
        kwargs["view"] = view

    ctx.stop_typing()
    sent = None
    try:
        sent = await ch.send(**kwargs)
        if sent is not None:
            ctx.last_bot_message = sent
        ctx.log_event("timer → sent the pending message before waiting")
    except discord.HTTPException as e:
        ctx.log_event(f"Failed to send the pending message before waiting: {e}")
    finally:
        ctx.text_buffer = ""
        ctx.embed_builders = {}
        ctx.view = None
    return sent is not None

# ─────────────────────────────────────────────────────────────
#  Editing an already-sent embed ($editEmbed / $editEmbedIn)
# ─────────────────────────────────────────────────────────────

def edit_target_channel(ctx):
    override = getattr(ctx, "_channel_override", None)
    if override is not None:
        return override
    interaction = getattr(ctx, "interaction", None)
    if interaction is not None and getattr(interaction, "channel", None) is not None:
        return interaction.channel
    return getattr(getattr(ctx, "message", None), "channel", None)


def build_edited_embeds(
    message,
    *,
    title: str | None = None,
    description: str | None = None,
    footer: str | None = None,
    color: int | None = None,
) -> list[discord.Embed] | None:
    if not message.embeds:
        return None

    embeds = list(message.embeds)
    e = embeds[0].copy()

    if title is not None:
        e.title = title
    if description is not None:
        e.description = description
    if color is not None:
        e.colour = discord.Colour(color)
    if footer is not None:
        e.set_footer(text=footer, icon_url=e.footer.icon_url)

    embeds[0] = e
    return embeds