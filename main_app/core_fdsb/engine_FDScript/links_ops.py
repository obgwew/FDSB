# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/links_ops.py

import re

import discord

_MD_LINK_RE = re.compile(
    r'\[([^\]\n]*)\]\(\s*<?(?:https?|ftp)://[^)\s]*>?(?:\s+"[^"]*")?\s*\)',
    re.IGNORECASE,
)

_BARE_LINK_RE = re.compile(
    r'<?(?:'
    r'(?:https?://)?(?:www\.)?(?:discord(?:app)?\.(?:gg|com/invite)|discord\.me)/[A-Za-z0-9_-]+'
    r'|(?:https?|ftp)://[^\s<>]*[^\s<>.,!?;:\'")\]]'
    r'|www\.[^\s<>]*[^\s<>.,!?;:\'")\]]'
    r')>?',
    re.IGNORECASE,
)

def _strip_links(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    out = []
    for line in text.split('\n'):
        new = _MD_LINK_RE.sub(r'\1', line)
        new = _BARE_LINK_RE.sub('', new)
        if new != line:
            new = re.sub(r'(?<=\S)[ \t]{2,}', ' ', new)
            new = re.sub(r'(?<=\S)[ \t]+(?=[.,!?;:](?:\s|$))', '', new).rstrip(' \t')
        out.append(new)
    return '\n'.join(out)

def _strip_embed_links(embed: discord.Embed) -> None:
    if embed.title:
        embed.title = _strip_links(embed.title) or None
    if embed.description:
        embed.description = _strip_links(embed.description) or None
    footer_text = getattr(embed.footer, 'text', None)
    if footer_text:
        embed.set_footer(
            text=_strip_links(footer_text) or "\u200b",
            icon_url=getattr(embed.footer, 'icon_url', None),
        )
    author_name = getattr(embed.author, 'name', None)
    if author_name:
        embed.set_author(
            name=_strip_links(author_name) or "\u200b",
            url=getattr(embed.author, 'url', None),
            icon_url=getattr(embed.author, 'icon_url', None),
        )
    for i, f in enumerate(list(embed.fields)):
        embed.set_field_at(
            i,
            name=_strip_links(f.name) or "\u200b",
            value=_strip_links(f.value) or "\u200b",
            inline=f.inline,
        )

def _apply_remove_links(ctx, args, kwargs, has_view: bool = False):
    if ctx is None or not getattr(ctx, 'remove_links', False):
        return args, kwargs, True

    args = list(args)
    kwargs = dict(kwargs)
    had_text = False
    changed = False

    if args and isinstance(args[0], str):
        had_text = bool(args[0].strip())
        new = _strip_links(args[0])
        changed |= new != args[0]
        args[0] = new
        remaining = new.strip()
    elif isinstance(kwargs.get('content'), str):
        had_text = bool(kwargs['content'].strip())
        new = _strip_links(kwargs['content'])
        changed |= new != kwargs['content']
        kwargs['content'] = new
        remaining = new.strip()
    else:
        remaining = ''

    embeds = list(kwargs.get('embeds') or [])
    if kwargs.get('embed') is not None:
        embeds.append(kwargs['embed'])
    for e in embeds:
        if isinstance(e, discord.Embed):
            _strip_embed_links(e)

    if changed:
        ctx.log_event("removeLinks → links removed from outgoing message")

    has_other = bool(
        embeds or has_view
        or kwargs.get('file') or kwargs.get('files')
        or kwargs.get('poll') or kwargs.get('stickers')
    )
    if had_text and not remaining and not has_other:
        ctx.log_event("removeLinks → message contained only links; nothing left to send")
        return tuple(args), kwargs, False
    return tuple(args), kwargs, True
