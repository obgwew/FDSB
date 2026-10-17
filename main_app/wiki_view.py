# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/wiki_view.py — Wiki tab (Flet 0.85.2+ / v1 API)

import os
import re
import json
import time
import asyncio
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable, Set

import flet as ft

from main_app.theme.theme_engine import ThemeEngine
from main_app.settings_app import get_current_lang
from main_app.langs._translations import Translations
from main_app.load.loading_view import LoadingScreen

try:
    from main_app.core_fdsb.server_FDScript import fgs_service as _fgs
except Exception:
    _fgs = None


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


GITHUB_RAW_BASE = "https://raw.githubusercontent.com/obgwew/FDSB/main/wiki"
GITHUB_API_BASE = "https://api.github.com/repos/obgwew/FDSB/contents/wiki"
REQUEST_TIMEOUT = 10 

_BLOCK_TAG_RE  = re.compile(r'<block([^>]*)>(.*?)</block>', re.DOTALL | re.IGNORECASE)
_BLOCK_ATTR_RE = re.compile(r'(\w+)\s*=\s*"?([^"\s]+)"?')

_CALLOUT_STYLES: Dict[str, Tuple[str, str, str]] = {
    'note':      ('#3B82F6', 'EDIT_OUTLINED',                    'callout_note'),
    'warning':   ('#F59E0B', 'WARNING_AMBER_ROUNDED',             'callout_limit'),
    'important': ('#EF4444', 'CLOSE_ROUNDED',                    'callout_important'),
    'question':  ('#22C55E', 'QUESTION_MARK_ROUNDED',             'callout_question'),
}
_CALLOUT_DEFAULT_ICON = 'INFO_OUTLINE_ROUNDED'

_CATEGORY_META: Dict[str, Tuple[str, str, str]] = {
    'command':  ('filter_command',  'TERMINAL_ROUNDED',     '#6366F1'),
    'event':    ('filter_event',    'BOLT_ROUNDED',          '#F59E0B'),
    'variable': ('filter_variable', 'DATA_OBJECT_ROUNDED',   '#8B5CF6'),
    'discord':  ('filter_discord',  'TAG_ROUNDED',           '#5865F2'),
    'time':     ('filter_time',     'SCHEDULE_ROUNDED',      '#10B981'),
}
_CATEGORY_DEFAULT_ICON  = 'LABEL_ROUNDED'
_CATEGORY_DEFAULT_COLOR = '#6B7280'

# {language: {normalized category name from the wiki data: canonical key}}
# Names come from the translation file (wiki_cat_<key>), nothing is hard-coded here.
_CATEGORY_NAME_CACHE: Dict[str, Dict[str, str]] = {}


def _normalize_category(cat: Optional[str]) -> str:
    return (cat or '').strip().lower()


def _category_names() -> Dict[str, str]:
    lang = get_current_lang() or 'en'
    names = _CATEGORY_NAME_CACHE.get(lang)
    if names is None:
        names = {}
        for key in _CATEGORY_META:
            label_key = f'wiki_cat_{key}'
            label = _normalize_category(_t(label_key))
            if label and label != label_key:
                names[label] = key
        _CATEGORY_NAME_CACHE[lang] = names
    return names


def _canonical_category(cat: Optional[str]) -> str:
    key = _normalize_category(cat)
    if key in _CATEGORY_META:
        return key
    return _category_names().get(key, key)


def _category_label(cat: str) -> str:
    key = _canonical_category(cat)
    if key in _CATEGORY_META:
        return _t(_CATEGORY_META[key][0])
    if key:
        return cat.strip()
    return _t('filter_other')


def _category_icon(cat: str) -> str:
    key = _canonical_category(cat)
    icon_name = _CATEGORY_META[key][1] if key in _CATEGORY_META else _CATEGORY_DEFAULT_ICON
    return getattr(ft.Icons, icon_name, ft.Icons.LABEL_ROUNDED)


def _category_color(cat: str) -> str:
    key = _canonical_category(cat)
    return _CATEGORY_META[key][2] if key in _CATEGORY_META else _CATEGORY_DEFAULT_COLOR


_HL_FUNC_COLOR = '#F1C40F'
_HL_FONT_SIZE   = 13
_HL_FONT_FAMILY = 'Consolas'

def _t(key: str) -> str:
    return Translations.get(key, get_current_lang() or 'en')


def _fmt_size(n: int) -> str:
    n = max(int(n or 0), 0)
    if n >= 1024 * 1024:
        return f'{n / (1024 * 1024):.2f} MB'
    return f'{n / 1024:.1f} KB'

def _wiki_lang() -> str:
    return (get_current_lang() or 'en').lstrip('_')

def _theme_unsub(cb):
    fn = getattr(ThemeEngine, 'unsubscribe', None)
    if callable(fn):
        try:
            fn(cb)
            return
        except Exception:
            pass
    for holder in (ThemeEngine, getattr(ThemeEngine, '_instance', None)):
        if holder is None:
            continue
        for val in list(vars(holder).values()):
            try:
                if isinstance(val, list) and cb in val:
                    val.remove(cb)
                elif isinstance(val, set) and cb in val:
                    val.discard(cb)
            except Exception:
                pass


@dataclass
class WikiParam:
    name: str
    type: str
    flag: str
    desc: str

@dataclass
class WikiDetails:
    syntax: str
    params:     List[WikiParam] = field(default_factory=list)
    examples:   List[str]       = field(default_factory=list)
    notes:      List[str]       = field(default_factory=list)
    warnings:   List[str]       = field(default_factory=list)
    importants: List[str]       = field(default_factory=list)
    questions:  List[str]       = field(default_factory=list)

@dataclass
class WikiDashBlock:
    type:    str = ''
    title:   str = ''
    kind:    str = ''
    items:   List[str]              = field(default_factory=list)
    options: List[Tuple[str, str]]  = field(default_factory=list)
    text:    str = ''
    image_id: str = ''
    caption:  str = ''

@dataclass
class WikiEntry:
    name:     str
    desc:     str
    category: str = ''
    details:  Optional[WikiDetails] = None
    blocks:   List[WikiDashBlock]   = field(default_factory=list)
    file_name: str = ''
    has_details: bool = False


class WikiParser:

    @staticmethod
    def _extract_block(text: str, tag: str) -> Optional[str]:
        open_tag, close_tag = f'<{tag}>', f'</{tag}>'
        start = text.find(open_tag)
        end   = text.find(close_tag)
        if start == -1 or end == -1 or end < start:
            return None
        return text[start + len(open_tag):end].strip('\n')

    @staticmethod
    def _strip_nested_blocks(text: str) -> str:
        return _BLOCK_TAG_RE.sub('', text)

    @staticmethod
    def _parse_dash(block: str) -> Optional[Dict[str, str]]:
        if block is None:
            return None
        data: Dict[str, str] = {}
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or ':' not in line:
                continue
            key, _, value = line.partition(':')
            data[key.strip().lower()] = value.strip()
        if not data.get('name') or not data.get('desc'):
            return None
        return data

    @staticmethod
    def _parse_dash_blocks(block: str) -> List[WikiDashBlock]:
        if not block:
            return []

        blocks: List[WikiDashBlock] = []
        for match in _BLOCK_TAG_RE.finditer(block):
            attrs_str, body = match.group(1), match.group(2)
            attrs = {k.lower(): v for k, v in _BLOCK_ATTR_RE.findall(attrs_str)}

            btype = attrs.get('type', '').strip().lower()
            if not btype:
                continue

            dash_block = WikiDashBlock(
                type=btype,
                title=attrs.get('title', '').strip(),
                kind=attrs.get('kind', '').strip().lower(),
            )

            for raw_line in body.splitlines():
                line = raw_line.strip()
                if not line or ':' not in line:
                    continue
                key, _, value = line.partition(':')
                key   = key.strip().lower()
                value = value.strip()

                try:
                    if key == 'item':
                        dash_block.items.append(value)
                    elif key == 'option':
                        parts = [p.strip() for p in value.split('|', 1)]
                        if len(parts) == 2 and parts[0]:
                            dash_block.options.append((parts[0], parts[1]))
                    elif key == 'text':
                        dash_block.text = (
                            f'{dash_block.text}\n{value}' if dash_block.text else value
                        )
                    elif key == 'id':
                        dash_block.image_id = value
                    elif key == 'caption':
                        dash_block.caption = value
                except Exception:
                    continue

            blocks.append(dash_block)

        return blocks

    @staticmethod
    def _parse_details(block: str) -> Optional[WikiDetails]:
        if block is None:
            return None

        syntax     = ''
        params:     List[WikiParam] = []
        examples:   List[str] = []
        notes:      List[str] = []
        warnings:   List[str] = []
        importants: List[str] = []
        questions:  List[str] = []

        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or ':' not in line:
                continue
            key, _, value = line.partition(':')
            key   = key.strip().lower()
            value = value.strip()

            try:
                if key == 'syntax':
                    syntax = value
                elif key == 'param':
                    parts = [p.strip() for p in value.split('|')]
                    if len(parts) < 4:
                        continue
                    params.append(WikiParam(name=parts[0], type=parts[1],
                                             flag=parts[2], desc=parts[3]))
                elif key == 'example':
                    examples.append(value)
                elif key == 'note':
                    notes.append(value)
                elif key == 'warning':
                    warnings.append(value)
                elif key == 'important':
                    importants.append(value)
                elif key == 'question':
                    questions.append(value)
            except Exception:
                continue

        if not syntax:
            return None

        return WikiDetails(syntax=syntax, params=params, examples=examples,
                            notes=notes, warnings=warnings,
                            importants=importants, questions=questions)

    @classmethod
    def parse_light(cls, text: str, file_name: str = '') -> Optional[WikiEntry]:
        dash_start = text.find('<dash>')
        dash_end = text.find('</dash>')
        if dash_start == -1 or dash_end == -1 or dash_end < dash_start:
            return None

        dash_content = text[dash_start + 6:dash_end]
        name = ''
        desc = ''
        category = ''

        for line in dash_content.splitlines():
            line = line.strip()
            if not line or ':' not in line:
                continue
            key, _, val = line.partition(':')
            k = key.strip().lower()
            v = val.strip()
            if k == 'name':
                name = v
            elif k == 'desc':
                desc = v
            elif k == 'category':
                category = v
            if name and desc and category:
                break

        if not name or not desc:
            return None

        has_details = ('<details>' in text and '</details>' in text)

        return WikiEntry(
            name=name,
            desc=desc,
            category=category,
            details=None,
            blocks=[],
            file_name=file_name,
            has_details=has_details,
        )

    @classmethod
    def parse_full(cls, text: str, file_name: str = '') -> Optional[WikiEntry]:
        try:
            dash_block = cls._extract_block(text, 'dash')
            if dash_block is None:
                return None

            dash_blocks = cls._parse_dash_blocks(dash_block)
            dash_data   = cls._parse_dash(cls._strip_nested_blocks(dash_block))
            if dash_data is None:
                return None

            details_block = cls._extract_block(text, 'details')
            details = cls._parse_details(details_block)

            return WikiEntry(
                name=dash_data['name'],
                desc=dash_data['desc'],
                category=dash_data.get('category', ''),
                details=details,
                blocks=dash_blocks,
                file_name=file_name,
                has_details=details is not None,
            )
        except Exception:
            return None


class WikiCache:

    @staticmethod
    def _base_dir() -> str:
        android_storage = os.getenv('FLET_APP_STORAGE_DATA')
        if android_storage:
            path = os.path.join(android_storage, 'wiki_cache')
        elif os.name == 'nt':
            root = os.getenv('APPDATA') or os.path.expanduser('~')
            path = os.path.join(root, 'FDScriptDashboard', 'wiki_cache')
        else:
            root = os.getenv('XDG_DATA_HOME') or os.path.join(
                os.path.expanduser('~'), '.local', 'share')
            path = os.path.join(root, 'FDScriptDashboard', 'wiki_cache')
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def lang_dir(cls, lang: str) -> str:
        path = os.path.join(cls._base_dir(), lang)
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def get_local_version(cls, lang: str) -> int:
        path = os.path.join(cls.lang_dir(lang), 'version.json')
        if not os.path.isfile(path):
            return 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return int(json.load(f).get('version', 0))
        except Exception:
            return 0

    @classmethod
    def set_local_version(cls, lang: str, version: int):
        path = os.path.join(cls.lang_dir(lang), 'version.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'version': version}, f)

    @classmethod
    def save_index(cls, lang: str, files: List[str]):
        path = os.path.join(cls.lang_dir(lang), 'index.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(files, f, ensure_ascii=False)

    @classmethod
    def load_index(cls, lang: str) -> List[str]:
        path = os.path.join(cls.lang_dir(lang), 'index.json')
        if not os.path.isfile(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def local_size(cls, lang: str) -> int:
        folder = os.path.join(cls.lang_dir(lang), 'functions')
        total = 0
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    if entry.is_file():
                        total += entry.stat().st_size
        except Exception:
            pass
        return total

    @classmethod
    def save_function_file_only(cls, lang: str, file_name: str, text: str) -> Optional[Dict]:
        folder = os.path.join(cls.lang_dir(lang), 'functions')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, file_name), 'w', encoding='utf-8') as f:
            f.write(text)

        entry = WikiParser.parse_light(text, file_name)
        if entry is not None:
            return cls._entry_meta(entry)
        return None

    @classmethod
    def _meta_path(cls, lang: str) -> str:
        return os.path.join(cls.lang_dir(lang), 'meta.json')

    @staticmethod
    def _entry_meta(entry: 'WikiEntry') -> Dict:
        return {
            'name':        entry.name,
            'desc':        entry.desc,
            'category':    entry.category,
            'file_name':   entry.file_name,
            'has_details': entry.has_details,
        }

    @classmethod
    def _load_meta_raw(cls, lang: str) -> List[Dict]:
        path = cls._meta_path(lang)
        if not os.path.isfile(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def _save_meta_raw(cls, lang: str, items: List[Dict]):
        items = sorted(items, key=lambda m: m.get('file_name', ''))
        with open(cls._meta_path(lang), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)

    @classmethod
    def _rebuild_meta(cls, lang: str) -> List[Dict]:
        folder = os.path.join(cls.lang_dir(lang), 'functions')
        items: List[Dict] = []
        if not os.path.isdir(folder):
            return items
        for file_name in sorted(os.listdir(folder)):
            path = os.path.join(folder, file_name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception:
                continue
            entry = WikiParser.parse_light(text, file_name)
            if entry is not None:
                items.append(cls._entry_meta(entry))
        if items:
            cls._save_meta_raw(lang, items)
        return items

    @classmethod
    def load_light_entries(cls, lang: str) -> List[WikiEntry]:
        raw = cls._load_meta_raw(lang)
        if not raw:
            raw = cls._rebuild_meta(lang)

        entries: List[WikiEntry] = []
        for m in raw:
            entries.append(WikiEntry(
                name=m.get('name', ''),
                desc=m.get('desc', ''),
                category=m.get('category', ''),
                details=None,
                blocks=[],
                file_name=m.get('file_name', ''),
                has_details=bool(m.get('has_details', False)),
            ))
        entries.sort(key=lambda e: e.file_name)
        return entries

    @classmethod
    def load_entry_full(cls, lang: str, file_name: str) -> Optional['WikiEntry']:
        if not file_name:
            return None
        path = os.path.join(cls.lang_dir(lang), 'functions', file_name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return None
        return WikiParser.parse_full(text, file_name)


class WikiRemote:

    @staticmethod
    def _get(url: str) -> str:
        req = urllib.request.Request(url, headers={'User-Agent': 'FDScriptDashboard'})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode('utf-8')

    @classmethod
    def fetch_version(cls, lang: str) -> int:
        url = f'{GITHUB_RAW_BASE}/{lang}/version.json'
        data = json.loads(cls._get(url))
        return int(data.get('version', 0))

    @classmethod
    def fetch_index(cls, lang: str) -> List[str]:
        url = f'{GITHUB_RAW_BASE}/{lang}/index.json'
        return json.loads(cls._get(url))

    @classmethod
    def fetch_sizes(cls, lang: str) -> Dict[str, int]:
        """{file_name: size_in_bytes} for the whole wiki folder in ONE request."""
        url = f'{GITHUB_API_BASE}/{lang}/functions'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'FDScriptDashboard',
            'Accept': 'application/vnd.github+json',
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            items = json.loads(resp.read().decode('utf-8'))
        return {it['name']: int(it.get('size', 0)) for it in items if it.get('type') == 'file'}

    @classmethod
    def fetch_function(cls, lang: str, file_name: str) -> str:
        url = f'{GITHUB_RAW_BASE}/{lang}/functions/{file_name}'
        return cls._get(url)

def _ink_btn(content: ft.Control, bgcolor: str, on_click,
             border_radius: int = 10, padding=None, width=None,
             disabled: bool = False) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=bgcolor if not disabled else _c('card_border'),
        border_radius=border_radius,
        padding=padding or ft.Padding(left=18, top=10, right=18, bottom=10),
        on_click=None if disabled else on_click,
        ink=not disabled,
        width=width,
        alignment=ft.Alignment(0, 0),
        opacity=0.5 if disabled else 1.0,
    )


def _badge(text: str, bgcolor: str, color: str = '#FFFFFF') -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=11, color=color, weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        border_radius=6,
        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
    )


def _tint(hex_color: str, opacity: int = 26) -> str:
    return f'#{opacity:02X}{hex_color.lstrip("#")}'


class BotWikiTab:
    def __init__(self, page: ft.Page, on_open_dashboard: Optional[Callable[[str], None]] = None):
        self._page              = page
        self._on_open_dashboard = on_open_dashboard
        self._lang              = _wiki_lang()
        
        self._entries: List[WikiEntry] = []
        self._filtered: List[WikiEntry] = []
        self._view_mode  = 'list'
        self._current: Optional[WikiEntry] = None
        
        self._full_cache: Dict[str, WikiEntry] = {}

        self._active_filters: Set[str] = set()
        self._busy = False
        self._hl_colors: Dict[str, str] = {}
        self._search_debounce_task: Optional[asyncio.Task] = None

        self._count_text = ft.Text(
            value="",
            size=12,
            color=_c('accent'), 
            weight=ft.FontWeight.BOLD,
        )

        self._header_title = ft.Text(
            _t('tab_wiki'), size=15, weight=ft.FontWeight.BOLD, color=_c('text'),
        )

        self._search_field = ft.TextField(
            hint_text=_t('search_hint'),
            height=40,
            width=180,
            content_padding=ft.Padding(left=10, right=10, top=0, bottom=0),
            bgcolor=_c('card_bg'),
            border_color=_c('card_border'),
            border_radius=8,
            on_change=self._on_search_change,
            suffix=ft.IconButton(
                icon=ft.Icons.CLEAR_ROUNDED,
                icon_size=16,
                icon_color=_c('text_dim'),
                tooltip=_t('clear_search'),
                on_click=self._clear_search,
            ),
        )

        self._filter_btn = ft.IconButton(
            icon=ft.Icons.FILTER_LIST_ROUNDED,
            icon_color=_c('accent'),
            tooltip=_t('filter_tooltip'),
            on_click=self._open_filter_sheet,
            on_long_press=self._reset_all_filters,
        )

        self._update_btn = ft.FloatingActionButton(
            icon=ft.Icons.SYNC_ROUNDED,
            bgcolor=_c('accent'),
            foreground_color='#FFFFFF',
            mini=True,
            tooltip=_t('check_updates'),
            on_click=self._check_updates,
        )

        self._header = ft.Container(
            content=ft.Row(
                [
                    self._header_title, 
                    self._search_field, 
                    self._filter_btn,
                    ft.Container(expand=True), 
                    self._count_text
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=12, right=12, top=10, bottom=10),
        )

        self._status_text = ft.Text(self._status_label(), size=12, color=_c('text_dim'))
        # Virtual (windowed) list: only a small window of cards exists at any time
        # (12 on first paint, never more than ~24). Everything above / below the
        # window is replaced by one empty spacer of the exact same height, so the
        # scrollbar and scroll position behave as if all cards were there.
        self._win_lo = 0
        self._win_hi = 0
        self._card_cache: Dict[int, ft.Control] = {}
        self._resetting   = False    # True while a search/filter redraw is scrolling to its target
        self._saved_offset = 0.0     # list scroll position remembered while a wiki page is open
        self._scroll_pix  = 0.0      # latest scroll position reported by Flutter
        self._scroll_view = 600.0    # latest viewport height
        self._last_pix    = 0.0
        self._going_down  = True
        self._sync_running = False
        # item_extent makes Flutter use a FIXED-extent list: every slot is exactly
        # _ITEM_EXT tall, so scroll extent / scrollbar thumb are exact (no estimating
        # from whichever children happen to be built). The cards that are not alive
        # are represented by the list's top/bottom padding, never by huge children.
        self._list_view = ft.ListView(
            expand=True, spacing=0, padding=ft.Padding(0, 0, 0, 70),
            item_extent=self._ITEM_EXT,
            on_scroll=self._on_list_scroll, scroll_interval=50,
        )

        self._list_root = ft.Column(
            [
                self._header,
                ft.Container(
                    content=ft.Stack(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [self._status_text, self._list_view],
                                    spacing=10,
                                    expand=True,
                                ),
                                padding=ft.Padding(left=12, right=12, top=8, bottom=0),
                                expand=True,
                            ),
                            ft.Container(
                                content=self._update_btn,
                                bottom=16,
                                right=16,
                                width=44,
                                height=44,
                                alignment=ft.Alignment(0, 0),
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

        self._build_sub_views()
        self._root = ft.Container(expand=True)
        ThemeEngine.subscribe(self._on_theme)

    def dispose(self):
        task = getattr(self, '_search_debounce_task', None)
        if task:
            task.cancel()
        self._view_mode = 'list'
        self._saved_offset = 0.0
        _theme_unsub(self._on_theme)

    def _build_sub_views(self):
        self._dash_back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color='#FFFFFF',
            bgcolor=_c('accent'), icon_size=16,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self._back_to_list,
        )
        self._dash_title = ft.Text('', size=18, weight=ft.FontWeight.BOLD, color=_c('text'))
        self._dash_body  = ft.Column(spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)
        self._dash_root = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self._dash_back_btn, self._dash_title], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    self._dash_body,
                ],
                spacing=14,
                expand=True,
            ),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
            expand=True,
        )

        self._detail_back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color='#FFFFFF',
            bgcolor=_c('accent'), icon_size=16,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self._back_to_list,
        )
        self._detail_title = ft.Text('', size=18, weight=ft.FontWeight.BOLD, color=_c('text'))
        self._detail_body   = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detail_root = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self._detail_back_btn, self._detail_title], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    self._detail_body,
                ],
                spacing=14,
                expand=True,
            ),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
            expand=True,
        )

    def _open_filter_sheet(self, _):
        found_cats = sorted(list({e.category.strip() for e in self._entries if e.category}))
        filter_col = ft.Column(spacing=10, tight=True)
        checkboxes: List[ft.Checkbox] = []

        def _close_sheet(_e=None):
            self._page.pop_dialog()

        def _reset_filters(_e=None):
            self._active_filters.clear()
            for cb in checkboxes:
                cb.value = False
            self._apply_filters()
            self._page.update()

        if not found_cats:
            filter_col.controls.append(
                ft.Container(
                    content=ft.Text(_t('no_categories'),
                                     color=_c('text_dim'), size=13),
                    padding=ft.Padding(0, 10, 0, 10),
                )
            )
        else:
            for raw in found_cats:
                canonical = _canonical_category(raw)
                label = _category_label(raw)

                cb = ft.Checkbox(
                    label=label,
                    value=canonical in self._active_filters,
                    on_change=lambda e, c=canonical: self._toggle_filter(c, e.control.value),
                    fill_color=_c('accent'),
                    label_style=ft.TextStyle(color=_c('text'), size=14),
                )
                checkboxes.append(cb)
                filter_col.controls.append(cb)

        header_row = ft.Row(
            [
                ft.Text(_t('filter_title'),
                        size=16, weight=ft.FontWeight.BOLD, color=_c('text')),
                ft.Container(expand=True),
                ft.TextButton(
                    content=ft.Text(_t('reset'), size=13,
                                     color=_c('accent'), weight=ft.FontWeight.W_600),
                    on_click=_reset_filters,
                    disabled=not found_cats,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE_ROUNDED,
                    icon_color=_c('text_dim'),
                    icon_size=18,
                    tooltip=_t('close'),
                    on_click=_close_sheet,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        apply_btn = _ink_btn(
            content=ft.Text(_t('done'), size=13, color='#FFFFFF',
                             weight=ft.FontWeight.W_600),
            bgcolor=_c('accent'),
            on_click=_close_sheet,
        )

        bs = ft.BottomSheet(
            ft.Container(
                content=ft.Column(
                    [
                        header_row,
                        ft.Divider(height=1, color=_c('card_border')),
                        filter_col,
                        ft.Container(height=10),
                        apply_btn,
                        ft.Container(height=10),
                    ],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=25,
                bgcolor=_c('card_bg'),
                border_radius=ft.BorderRadius(top_left=20, top_right=20, bottom_left=0, bottom_right=0),
            ),
        )
        self._page.show_dialog(bs)

    def _toggle_filter(self, category: str, is_active: bool):
        if is_active:
            self._active_filters.add(category)
        else:
            if category in self._active_filters:
                self._active_filters.remove(category)
        
        self._apply_filters()
        self._page.update()

    def _clear_search(self, _e=None):
        self._search_field.value = ""
        self._apply_filters()
        self._page.update()

    def _reset_all_filters(self, _e=None):
        self._active_filters.clear()
        self._apply_filters()
        self._page.update()

    def swipe_blocked(self) -> bool:
        return self._busy or self._view_mode != 'list'

    def handle_back(self) -> bool:
        if self._view_mode != 'list':
            self._back_to_list(None)
            return True
        return False

    def guard_tab_change(self, on_proceed: callable, on_cancel: callable = None):
        # Leaving the Wiki for another tab (Settings, Variables, ...) keeps it exactly
        # as it is: the list at its scroll position, or the open dashboard / detail
        # page. It is only reset when the bot dashboard itself is left for the main
        # FDSB view (dispose() + a brand-new BotWikiTab next time).
        self._remember_list_position()
        on_proceed and on_proceed()

    def _remember_list_position(self):
        if self._view_mode == 'list' and self._filtered and not self._resetting:
            self._saved_offset = self._scroll_pix

    def on_show(self):
        if not self._entries:
            self._page.run_task(self._async_load_bot_task)
            return
        self._render()
        if self._page:
            self._page.update()
            if self._view_mode == 'list' and self._filtered:
                # The dashboard calls on_show BEFORE it slides this tab's slot in, so
                # the list is not mounted yet. Flutter also lost its scroll offset while
                # the tab was hidden. Re-apply the saved offset a few times, spread over
                # the slide animation, so at least one attempt lands on a mounted list.
                self._restore_list_position(delay=0.05, settle=(0.0, 0.2, 0.4))
            else:
                self._resetting = False

    def on_hide(self):
        self._remember_list_position()
        if self._view_mode == 'list' and self._filtered:
            # ignore scroll events while the list is detached / being re-mounted, so a
            # bogus position can never move the card window away from the saved one
            self._resetting = True

    def _is_rtl(self) -> bool:
        return (self._lang or '').lower() in ('ar', 'fa', 'ur')

    def _status_label(self) -> str:
        v = WikiCache.get_local_version(self._lang)
        if v == 0 and not self._entries:
            return _t('no_cache')
        label = _t('up_to_date').format(v=v)
        size = WikiCache.local_size(self._lang)
        if size > 0:
            label = f'{label} • {_fmt_size(size)}'
        return label

    def _card_border(self) -> ft.Border:
        return ft.Border(
            left=ft.BorderSide(1, _c('card_border')),
            top=ft.BorderSide(1, _c('card_border')),
            right=ft.BorderSide(1, _c('card_border')),
            bottom=ft.BorderSide(1, _c('card_border')),
        )

    def _on_theme(self, data: dict):
        get = lambda k: data.get(k, '#888888')
        self._header_title.color        = get('text')
        self._count_text.color          = get('accent')
        self._search_field.bgcolor      = get('card_bg')
        self._search_field.border_color = get('card_border')
        self._status_text.color         = get('text_dim')
        self._update_btn.bgcolor        = get('accent')
        self._dash_back_btn.bgcolor     = get('accent')
        self._dash_title.color          = get('text')
        self._detail_back_btn.bgcolor   = get('accent')
        self._detail_title.color        = get('text')

        self._hl_colors = {
            'base':    get('success'),
            'control': get('syntax_control_flow'),
            'func':    data.get('syntax_func', _HL_FUNC_COLOR),
            'known':   get('syntax_cmd'),
            'bracket': get('syntax_brackets'),
            'semi':    get('syntax_semicolon'),
            'string':  get('warning'),
            'comment': get('text_dim'),
        }
        if self._filtered:
            self._card_cache.clear()
            self._apply_window()
        self._render()
        if self._page:
            self._page.update()

    def build(self) -> ft.Control:
        self._lang = _wiki_lang()
        if not self._busy:
            self._render()
        return self._root

    def _render(self):
        if self._busy:
            return
        if self._view_mode == 'list':
            self._root.content = self._list_root
        elif self._view_mode == 'dash':
            self._root.content = self._dash_root
        else:
            self._root.content = self._detail_root

    def _on_search_change(self, e):
        if self._search_debounce_task:
            self._search_debounce_task.cancel()
        
        async def _debounced():
            await asyncio.sleep(0.18)
            self._apply_filters()
            if self._page:
                self._page.update()

        self._search_debounce_task = self._page.run_task(_debounced)

    def _update_wiki_count(self):
        count = len(self._filtered)
        self._count_text.value = _t('total_wiki_count').format(count=count)

    def _apply_filters(self):
        query = (self._search_field.value or '').strip().lower()
        result = list(self._entries)

        if self._active_filters:
            result = [
                en for en in result
                if _canonical_category(en.category) in self._active_filters
            ]

        if query:
            result = [
                en for en in result
                if query in en.name.lower() or query in en.desc.lower()
            ]

        self._filtered = result
        self._update_wiki_count()
        self._rebuild_list()

    # ── windowed list ────────────────────────────────────────────────────────
    _CARD_H   = 152                 # fixed card height  -> exact scroll maths
    _GAP      = 12                  # space between cards
    _ITEM_EXT = _CARD_H + _GAP      # height one slot takes in the list
    _WIN_STEP = 12                  # cards added/removed per step
    _WIN_MAX  = 24                  # max cards alive at once

    def _rebuild_list(self, target: int = 0):
        """Search / filter changed: delete every live card, then redraw only the
        window around `target` (12 cards above it, 12 below). target=0 is the
        first result, so a new search starts with its first 12 matches."""
        self._card_cache.clear()
        self._list_view.controls = []
        n = len(self._filtered)

        self._last_pix = 0.0
        self._scroll_pix = 0.0
        self._going_down = True

        if n == 0:
            self._win_lo = self._win_hi = 0
            self._list_view.item_extent = None
            self._list_view.padding = ft.Padding(0, 0, 0, 70)
            self._list_view.controls = [
                ft.Container(
                    content=ft.Text(_t('no_results'), color=_c('text_dim'), size=13,
                                     text_align=ft.TextAlign.CENTER),
                    padding=40,
                    alignment=ft.Alignment(0, 0),
                )
            ]
            return

        target = max(0, min(target, n - 1))
        self._win_lo = max(0, target - self._WIN_STEP)
        self._win_hi = min(n, target + self._WIN_STEP)
        self._apply_window()
        self._saved_offset = target * self._ITEM_EXT
        self._scroll_list_to(self._saved_offset)

    def _scroll_list_to(self, offset: float, delay: float = 0.0, settle: tuple = (0.0,)):
        self._resetting = True

        async def _go():
            try:
                if delay:
                    await asyncio.sleep(delay)
                for pause in settle:
                    if pause:
                        await asyncio.sleep(pause)
                    for _attempt in range(5):
                        try:
                            await self._list_view.scroll_to(offset=offset, duration=0)
                            break
                        except Exception:
                            # list may not be mounted yet right after a view switch
                            await asyncio.sleep(0.06)
            finally:
                self._scroll_pix = offset
                self._last_pix = offset
                self._resetting = False
        try:
            self._page.run_task(_go)
        except Exception:
            self._resetting = False

    def _apply_window(self):
        """Materialise cards [lo, hi); stand in for all the others with padding."""
        n, lo, hi = len(self._filtered), self._win_lo, self._win_hi
        ext = self._ITEM_EXT

        # drop cards that left the window (this is what frees the UI objects)
        for idx in [i for i in self._card_cache if i < lo or i >= hi]:
            del self._card_cache[idx]

        controls: List[ft.Control] = []
        for idx in range(lo, hi):
            card = self._card_cache.get(idx)
            if card is None:
                card = self._build_slot(self._filtered[idx])
                self._card_cache[idx] = card
            controls.append(card)

        # total extent = top + cards + bottom is ALWAYS n * ext (+70 bottom margin)
        self._list_view.item_extent = ext
        self._list_view.padding = ft.Padding(0, lo * ext, 0, (n - hi) * ext + 70)
        self._list_view.controls = controls

    def _on_list_scroll(self, e):
        """Only record the newest position; one worker applies it.

        Scroll events can arrive faster than the UI can be patched. Handling each
        one directly lets old positions overwrite newer ones (the up/down desync),
        so events are coalesced and the window always follows the LATEST position.
        """
        if self._resetting:
            return
        self._scroll_pix  = max(0.0, float(e.pixels or 0))
        self._scroll_view = float(getattr(e, 'viewport_dimension', 0) or 600)
        if self._sync_running or len(self._filtered) <= self._WIN_STEP:
            return
        self._sync_running = True
        try:
            self._page.run_task(self._sync_window_task)
        except Exception:
            self._sync_running = False

    async def _sync_window_task(self):
        try:
            while True:
                pix = self._scroll_pix
                if self._move_window(pix, self._scroll_view):
                    self._list_view.update()
                await asyncio.sleep(0.04)
                if self._scroll_pix == pix:     # position settled -> done
                    break
        except Exception as ex:
            print(f'[Wiki] window sync failed: {ex}')
        finally:
            self._sync_running = False

    _AHEAD_MIN  = 5    # cards that must exist in the direction of travel
    _BEHIND_MIN = 2    # and behind it
    _BEHIND_KEEP = 4   # cards kept behind the viewport when the window is moved

    def _move_window(self, pix: float, view: float) -> bool:
        n = len(self._filtered)
        if n <= self._WIN_STEP:
            return False

        ext   = self._ITEM_EXT
        first = min(n - 1, int(pix // ext))
        last  = min(n - 1, int((pix + view) // ext))
        vis   = last - first + 1

        delta = pix - self._last_pix
        if abs(delta) >= 2:
            self._going_down = delta > 0
        self._last_pix = pix
        down = self._going_down

        lo, hi = self._win_lo, self._win_hi
        cap = max(self._WIN_MAX, vis + self._WIN_STEP)

        below = (hi - 1 - last) if hi < n else 10 ** 6   # cards ready under the viewport
        above = (first - lo)    if lo > 0 else 10 ** 6   # cards ready over the viewport
        ahead, behind = (below, above) if down else (above, below)

        covered = first >= lo and last < hi
        if covered and ahead >= self._AHEAD_MIN and behind >= self._BEHIND_MIN:
            return False

        # Move the window so most of its 24 slots lie in the direction of travel.
        keep = self._BEHIND_KEEP if down else cap - vis - self._BEHIND_KEEP
        new_lo = max(0, min(first - keep, n - cap))
        new_hi = min(n, new_lo + cap)
        if (new_lo, new_hi) == (lo, hi):
            return False

        self._win_lo, self._win_hi = new_lo, new_hi
        self._apply_window()
        return True

    def _build_slot(self, entry: WikiEntry) -> ft.Container:
        """Fixed-height slot = card + gap, so positions are exact multiples of _ITEM_EXT."""
        return ft.Container(
            content=self._build_card(entry),
            height=self._ITEM_EXT,
            padding=ft.Padding(0, 0, 0, self._GAP),
        )

    def _build_card(self, entry: WikiEntry) -> ft.Container:
        rtl = self._is_rtl()

        title_row = [
            ft.Text(entry.name, size=15, weight=ft.FontWeight.BOLD, color=_c('text'),
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand_loose=True),
        ]
        if entry.category:
            title_row.append(_badge(_category_label(entry.category), _category_color(entry.category)))

        def _action(icon, label, handler) -> ft.Container:
            return _ink_btn(
                content=ft.Row(
                    [ft.Icon(icon, color='#FFFFFF', size=16),
                     ft.Text(label, color='#FFFFFF', size=12.5, weight=ft.FontWeight.W_600)],
                    spacing=7, tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=_c('accent'),
                on_click=handler,
                border_radius=10,
                padding=ft.Padding(left=14, top=9, right=14, bottom=9),
            )

        buttons = [
            _action(ft.Icons.SPACE_DASHBOARD_ROUNDED, _t('open_dashboard'),
                    lambda e, en=entry: self._page.run_task(self._async_open_dash, en)),
        ]
        if entry.has_details:
            buttons.append(
                _action(ft.Icons.INFO_OUTLINE_ROUNDED, _t('function_info'),
                        lambda e, en=entry: self._page.run_task(self._async_open_detail, en))
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(title_row, spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        content=ft.Text(entry.desc, size=13, color=_c('text_dim'), rtl=rtl,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        height=42,
                    ),
                    ft.Row(buttons, spacing=10),
                ],
                spacing=4,
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            height=self._CARD_H,
            bgcolor=_c('card_bg'),
            border=self._card_border(),
            border_radius=14,
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            rtl=rtl,
        )

    def _rich_paragraph(self, text: str, size: int = 14, color: Optional[str] = None) -> ft.Text:
        color = color or _c('text')
        spans = []
        parts = (text or '').split('`')
        for i, part in enumerate(parts):
            if not part: continue
            if i % 2 == 1:
                spans.append(ft.TextSpan(part, style=ft.TextStyle(font_family='monospace', color=_c('accent'), bgcolor=_tint(_c('accent'), 22), size=size)))
            else:
                spans.append(ft.TextSpan(part, style=ft.TextStyle(color=color, size=size)))
        return ft.Text(spans=spans, size=size, rtl=self._is_rtl())

    def _highlight_code(self, text: str) -> List[ft.TextSpan]:
        colors = self._hl_colors
        base_color = colors.get('base', '#2ECC71')
        def _span(v, c): return ft.TextSpan(v, ft.TextStyle(color=c, size=_HL_FONT_SIZE, font_family=_HL_FONT_FAMILY))
        spans = []
        pattern = re.compile(r'(?P<comment>#.*)|(?P<string>".*?"|\'.*?\')|(?P<token>\$\w*)|(?P<punct>[\[\];])|(?P<text>[^#"\'$\[\];]+)')
        for match in pattern.finditer(text):
            val, grp = match.group(), match.lastgroup
            col = colors.get(grp, base_color)
            spans.append(_span(val, col))
        return spans

    def _code_box(self, text: str, with_copy: bool = False) -> ft.Control:
        box = ft.Container(content=ft.Text(spans=self._highlight_code(text), selectable=True), bgcolor='#0D1117', border_radius=10, padding=14)
        if not with_copy: return box
        return ft.Row([ft.Container(box, expand=True), ft.IconButton(icon=ft.Icons.COPY_ROUNDED, icon_color=_c('text_dim'), icon_size=18, on_click=self._make_copy_handler(text))], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _make_copy_handler(self, text: str) -> Callable:
        async def _handler(e): await self._copy_syntax(e, text)
        return _handler

    async def _copy_syntax(self, e, text: str):
        try:
            await ft.Clipboard().set(text)
            self._page.show_dialog(ft.SnackBar(content=ft.Text(_t('copied')), duration=1400))
        except: pass

    def _render_dash_block(self, block: WikiDashBlock) -> ft.Control:
        if block.type == 'toc':
            chips = []
            for i, item in enumerate(block.items):
                if i > 0: chips.append(ft.Text('>', size=13, color=_c('text_dim')))
                chips.append(ft.Text(item, size=13, color=_c('accent'), weight=ft.FontWeight.W_600))
            return ft.Column([ft.Row(chips, wrap=True, spacing=8)], spacing=10)
        if block.type == 'list':
            col = [ft.Text(block.title, size=15, weight=ft.FontWeight.BOLD) if block.title else ft.Container()]
            for item in block.items: col.append(ft.Row([ft.Text('•'), self._pill(item)], spacing=8))
            return ft.Column(col, spacing=8)
        if block.type == 'options':
            col = [ft.Text(block.title, size=15, weight=ft.FontWeight.BOLD) if block.title else ft.Container()]
            for l, d in block.options: col.append(ft.Row([self._pill(l), ft.Text(f'- {d}', size=13)], spacing=8))
            return ft.Column(col, spacing=10)
        if block.type == 'text': return ft.Column([self._rich_paragraph(block.text)], spacing=8)
        if block.type == 'code': return self._code_box(block.text, with_copy=True)
        if block.type == 'callout':
            c, i, l = self._callout_style(block.kind)
            return self._callout(l, block.text, c, i)
        if block.type == 'image':
            img = ft.Image(src=f"exm_img/{block.image_id}.png", border_radius=8, fit=ft.ImageFit.CONTAIN)
            return ft.Column([ft.Container(img, alignment=ft.Alignment(0,0)), ft.Text(block.caption, size=12, color=_c('text_dim'))], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Container()

    def _callout_style(self, kind: str) -> Tuple[str, str, str]:
        color, icon_name, key = _CALLOUT_STYLES.get(kind, ('#3B82F6', _CALLOUT_DEFAULT_ICON, 'callout_note'))
        return color, getattr(ft.Icons, icon_name, ft.Icons.INFO_OUTLINE_ROUNDED), _t(key)

    def _callout(self, title: str, text: str, color: str, icon) -> ft.Container:
        return ft.Container(content=ft.Column([ft.Row([ft.Icon(icon, color=color, size=18), ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=color)], spacing=8), ft.Text(text, size=13, color=_c('text'), rtl=self._is_rtl())], spacing=6), bgcolor=_tint(color, 24), border=ft.Border(left=ft.BorderSide(4, color)), border_radius=10, padding=12, rtl=self._is_rtl())

    def _pill(self, text: str) -> ft.Container:
        return ft.Container(content=ft.Text(text, size=12, color=_c('accent'), font_family='monospace', weight=ft.FontWeight.W_600), bgcolor=_tint(_c('accent'), 24), border_radius=6, padding=ft.Padding(10, 4, 10, 4))

    async def _get_full_entry(self, entry: WikiEntry) -> WikiEntry:
        if entry.file_name in self._full_cache:
            return self._full_cache[entry.file_name]

        full_entry = await asyncio.get_event_loop().run_in_executor(
            None, WikiCache.load_entry_full, self._lang, entry.file_name
        )
        resolved = full_entry or entry
        self._full_cache[entry.file_name] = resolved
        return resolved

    async def _async_open_dash(self, entry: WikiEntry):
        self._saved_offset = self._scroll_pix
        self._view_mode = 'dash'
        self._render()
        self._page.update()

        full_entry = await self._get_full_entry(entry)
        self._dash_title.value = full_entry.name
        controls = [self._rich_paragraph(full_entry.desc)]
        for b in full_entry.blocks: 
            controls.append(self._render_dash_block(b))
        self._dash_body.controls = controls
        self._render()
        self._page.update()

    async def _async_open_detail(self, entry: WikiEntry):
        self._saved_offset = self._scroll_pix
        self._view_mode = 'detail'
        self._render()
        self._page.update()

        full_entry = await self._get_full_entry(entry)
        if not full_entry or not full_entry.details: 
            self._back_to_list(None)
            return

        self._detail_title.value = f'{full_entry.name}'
        self._build_detail_body(full_entry)
        self._render()
        self._page.update()

    def _back_to_list(self, _):
        self._view_mode = 'list'
        self._render()
        if self._page:
            self._page.update()
            self._restore_list_position()

    def _restore_list_position(self, delay: float = 0.0, settle: tuple = (0.0,)):
        """The list is removed from the page while a wiki page is open, so Flutter
        forgets its scroll offset. Put it back exactly where the user left it
        (the card window / padding in memory already match that position)."""
        if self._filtered:
            self._scroll_list_to(self._saved_offset, delay, settle)

    def _build_detail_body(self, entry: WikiEntry):
        det = entry.details
        controls = [ft.Text(entry.desc, size=13, color=_c('text_dim')), self._code_box(det.syntax, True)]
        if det.params:
            for p in det.params:
                controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([ft.Text(p.name, weight='bold', color=_c('text')), _badge(p.type, '#6366F1'), _badge(p.flag, '#3B82F6')], spacing=6),
                                ft.Text(p.desc, size=12, color=_c('text_dim'))
                            ],
                            spacing=4,
                        ),
                        bgcolor=_c('card_bg'),
                        border=self._card_border(),
                        border_radius=8,
                        padding=10,
                    )
                )
        if det.examples:
            for ex in det.examples: 
                controls.append(self._code_box(ex, True))
        self._detail_body.controls = controls

    def _set_busy(self, busy: bool, label: str = ''):
        self._busy = busy
        self._update_btn.opacity = 0.6 if busy else 1.0
        if label: self._status_text.value = label
        if not busy:
            self._render()
        self._page.update()

    async def _notify(self, title: str, body: str, done: bool = False):
        if _fgs is None:
            return
        try:
            await _fgs.show_download_notification(title, body, done=done, page=self._page)
        except Exception as ex:
            print(f'[Wiki] notification failed: {ex}')

    async def _check_updates(self, e):
        if self._busy:
            return
        self._set_busy(True, _t('checking'))

        loop = asyncio.get_event_loop()
        lang = self._lang

        try:
            remote_version = await loop.run_in_executor(None, WikiRemote.fetch_version, lang)
        except Exception as ex:
            print(f'[Wiki] fetch_version failed: {ex}')
            self._set_busy(False, _t('update_failed'))
            return

        local_version = WikiCache.get_local_version(lang)

        if remote_version <= local_version:
            self._set_busy(False, self._status_label())
            return

        try:
            index = await loop.run_in_executor(None, WikiRemote.fetch_index, lang)
        except Exception as ex:
            print(f'[Wiki] fetch_index failed: {ex}')
            self._set_busy(False, _t('update_failed'))
            return
        index.sort()

        # Total download size (one GitHub API request). If it fails we just hide the size.
        try:
            sizes = await loop.run_in_executor(None, WikiRemote.fetch_sizes, lang)
        except Exception as ex:
            print(f'[Wiki] fetch_sizes failed: {ex}')
            sizes = {}
        total_bytes = sum(sizes.get(fn, 0) for fn in index)
        total_txt = _fmt_size(total_bytes) if total_bytes > 0 else ''

        base_title = _t('downloading')
        title = f'{base_title} ({total_txt})' if total_txt else base_title

        total = len(index) or 1
        stats = {'bytes': 0, 'done': 0, 'last_notif': 0.0}

        def _progress_text() -> str:
            txt = f'{stats["done"]}/{total} • {_fmt_size(stats["bytes"])}'
            return f'{txt} / {total_txt}' if total_txt else txt

        def _notif_text() -> str:
            pct = int(stats['done'] * 100 / total)
            txt = f'{pct}% • {_fmt_size(stats["bytes"])}'
            return f'{txt} / {total_txt}' if total_txt else txt

        # Android: ask for notification permission, then show the first notification
        if _fgs is not None:
            _fgs.ensure_background_mode(self._page)
            await _fgs.ensure_notification_permission()
        await self._notify(base_title, _notif_text())

        self._page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, color='#FFFFFF', size=20),
                        ft.Text(title, color='#FFFFFF', size=14, weight=ft.FontWeight.W_600),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=_c('accent'),
                duration=4000,
            )
        )

        loader = LoadingScreen(container=self._root, page=self._page, title=title)

        async def _do_download(screen: LoadingScreen):
            screen.set_progress(0.0, _progress_text())

            async def _fetch_one(file_name: str):
                text = await loop.run_in_executor(None, WikiRemote.fetch_function, lang, file_name)
                await loop.run_in_executor(None, WikiCache.save_function_file_only, lang, file_name, text)
                stats['done'] += 1
                stats['bytes'] += len(text.encode('utf-8'))
                screen.set_progress(stats['done'] / total, _progress_text())

                # throttle: at most one notification update per second
                now = time.monotonic()
                if now - stats['last_notif'] >= 1.0:
                    stats['last_notif'] = now
                    await self._notify(base_title, _notif_text())

            chunk_size = 45
            for i in range(0, len(index), chunk_size):
                chunk = index[i:i + chunk_size]
                await asyncio.gather(*[_fetch_one(fn) for fn in chunk])
                await asyncio.sleep(0.5)

            await loop.run_in_executor(None, WikiCache._rebuild_meta, lang)
            WikiCache.save_index(lang, index)
            WikiCache.set_local_version(lang, remote_version)

        try:
            await loader.run(
                _do_download,
                done_message=_t('up_to_date').format(v=remote_version),
                extra_hold_max=5.0,
            )
        except Exception as ex:
            print(f'[Wiki] update download failed: {ex}')
            await self._notify(base_title, _t('update_failed'), done=True)
            self._set_busy(False, _t('update_failed'))
            return

        self._full_cache.clear()
        self._entries = WikiCache.load_light_entries(lang)
        self._apply_filters()
        self._set_busy(False, self._status_label())

        await self._notify(
            _t('wiki_download_done'),
            f'{_t("up_to_date").format(v=remote_version)} • {_fmt_size(stats["bytes"])}',
            done=True,
        )

        self._page.show_dialog(
            ft.SnackBar(content=ft.Text(_t('up_to_date').format(v=remote_version)), duration=2500)
        )

    def load_bot(self, *_args, **_kwargs):
        if self._entries:
            return
        self._page.run_task(self._async_load_bot_task)

    async def _async_load_bot_task(self, *args):
        self._entries = await asyncio.get_event_loop().run_in_executor(None, WikiCache.load_light_entries, self._lang)
        self._apply_filters()
        if self._page:
            self._page.update()

    def select_events_filter(self):
        self._view_mode = 'list'
        self._active_filters = {'event'}
        self._search_field.value = ""
        self._apply_filters()
        self._render()
        if self._page:
            self._page.update()