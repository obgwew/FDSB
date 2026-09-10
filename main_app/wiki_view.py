# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/wiki_view.py — Wiki tab (Flet 0.85.2+ / v1 API)

from operator import index
import os
import re
import json
import asyncio
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable, Set

import flet as ft

from main_app.theme.theme_engine import ThemeEngine
from main_app.settings import get_current_lang
from main_app.langs.translations import Translations
from main_app.load.loading_view import LoadingScreen


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


GITHUB_RAW_BASE = "https://raw.githubusercontent.com/obgwew/FDSB/main/wiki"

REQUEST_TIMEOUT = 10 

_BLOCK_TAG_RE  = re.compile(r'<block([^>]*)>(.*?)</block>', re.DOTALL | re.IGNORECASE)
_BLOCK_ATTR_RE = re.compile(r'(\w+)\s*=\s*"?([^"\s]+)"?')

_CALLOUT_STYLES: Dict[str, Tuple[str, str, str, str]] = {
    'note':      ('#3B82F6', 'EDIT_OUTLINED',                    'callout_note',        'Note'),
    'warning':   ('#F59E0B', 'WARNING_AMBER_ROUNDED',             'callout_limit',       'Limit'),
    'important': ('#EF4444', 'CLOSE_ROUNDED',                    'callout_important',   "It's important!"),
    'question':  ('#22C55E', 'QUESTION_MARK_ROUNDED',             'callout_question',   'What is this?'),
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

_CATEGORY_ALIASES: Dict[str, str] = {
    'event':                   'event',
    'الحدث':                   'event',
    'événement':               'event',
    'ereignis':                'event',
    'variables':               'variable',
    'المتغيرات':               'variable',
    'variablen':               'variable',
    'timing & delays':         'time',
    'التوقيت والتأخير':         'time',
    'minutage & délais':       'time',
    'timing & verzögerungen':  'time',
}


def _normalize_category(cat: Optional[str]) -> str:
    return (cat or '').strip().lower()


def _canonical_category(cat: Optional[str]) -> str:
    key = _normalize_category(cat)
    if key in _CATEGORY_META:
        return key
    return _CATEGORY_ALIASES.get(key, key)


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

try:
    from main_app.core_fdsb.FDCore import (
        KNOWN_COMMANDS, CONTROL_FLOW_COMMANDS, FUNCTION_COMMANDS,
    )
except ImportError:
    KNOWN_COMMANDS = set()
    CONTROL_FLOW_COMMANDS = {
        "if", "elif", "else", "endif", "while", "endwhile", "for", "endfor",
        "break", "return", "and", "or", "onlyIf", "onlyAdmin", "log"
    }
    FUNCTION_COMMANDS = {"func", "endfunc", "call"}

_HL_FUNC_COLOR = '#F1C40F'
_HL_FONT_SIZE   = 13
_HL_FONT_FAMILY = 'Consolas'

def _t(key: str) -> str:
    return Translations.get(key, get_current_lang() or 'en')

def _t_or_fallback(key: str, fallback: str = '') -> str:
    try:
        val = _t(key)
    except Exception:
        val = None
    if not val or val == key:
        return fallback
    return val

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
    def parse(cls, text: str, file_name: str = '') -> Optional[WikiEntry]:
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
    def save_function_file_only(cls, lang: str, file_name: str, text: str) -> Optional[Dict]:
        folder = os.path.join(cls.lang_dir(lang), 'functions')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, file_name), 'w', encoding='utf-8') as f:
            f.write(text)

        entry = WikiParser.parse(text, file_name)
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
            'has_details': entry.details is not None,
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
            entry = WikiParser.parse(text, file_name)
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
        return WikiParser.parse(text, file_name)


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
        self._lang    = get_current_lang() or 'en'
        
        self._entries: List[WikiEntry] = []
        self._filtered: List[WikiEntry] = []
        self._view_mode  = 'list'
        self._current: Optional[WikiEntry] = None
        
        # نظام الفلاتر النشطة (اختيار متعدد)
        self._active_filters: Set[str] = set()
        self._busy = False
        self._hl_colors: Dict[str, str] = {}

        # ── العداد (أقصى اليمين) ──────────────────────────────────
        self._count_text = ft.Text(
            value="",
            size=12,
            color=_c('accent'), 
            weight=ft.FontWeight.BOLD,
        )

        self._header_title = ft.Text(
            _t('tab_wiki'), size=15, weight=ft.FontWeight.BOLD, color=_c('text'),
        )

        # ── مربع البحث (على اليسار بجانب العنوان) ──────────────────────
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
                tooltip=_t('clear_search') or "مسح البحث",
                on_click=self._clear_search,
            ),
        )

        # ── زر الفلترة (بجانب البحث) ───────────────────────────
        self._filter_btn = ft.IconButton(
            icon=ft.Icons.FILTER_LIST_ROUNDED,
            icon_color=_c('accent'),
            tooltip=_t('filter_tooltip') or "Filter",
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

        # ── الهيدر الرئيسي ──
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
        self._list_view = ft.ListView(expand=True, spacing=10, padding=ft.Padding(0, 0, 0, 70))

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

    def _build_sub_views(self):
        # واجهة الـ Dash
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

        # واجهة التفاصيل (Detail)
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
        # استخراج التصنيفات وبناء قائمة الخيارات
        found_cats = sorted(list({e.category.strip() for e in self._entries if e.category}))
        filter_col = ft.Column(spacing=10, tight=True)
        checkboxes: List[ft.Checkbox] = []

        def _close_sheet(_e=None):
            # إغلاق البوتوم شيت - النظير الصحيح لـ page.close() في هذا الإصدار
            self._page.pop_dialog()

        def _reset_filters(_e=None):
            # مسح كل الفلاتر النشطة وإعادة تحديد كل الـ checkboxes
            self._active_filters.clear()
            for cb in checkboxes:
                cb.value = False
            self._apply_filters()
            self._page.update()

        if not found_cats:
            filter_col.controls.append(
                ft.Container(
                    content=ft.Text(_t('no_categories') or "لا توجد تصنيفات بعد",
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

        # ── هيدر الشيت: عنوان + زر ريسيت + زر إغلاق (X) ──
        header_row = ft.Row(
            [
                ft.Text(_t('filter_title') or "Categories / التصنيفات",
                        size=16, weight=ft.FontWeight.BOLD, color=_c('text')),
                ft.Container(expand=True),
                ft.TextButton(
                    content=ft.Text(_t('reset') or "إعادة تعيين", size=13,
                                     color=_c('accent'), weight=ft.FontWeight.W_600),
                    on_click=_reset_filters,
                    disabled=not found_cats,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE_ROUNDED,
                    icon_color=_c('text_dim'),
                    icon_size=18,
                    tooltip=_t('close') or "إغلاق",
                    on_click=_close_sheet,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ── زر تطبيق/إغلاق سفلي واضح للمستخدم ──
        apply_btn = _ink_btn(
            content=ft.Text(_t('done') or "تم", size=13, color='#FFFFFF',
                             weight=ft.FontWeight.W_600),
            bgcolor=_c('accent'),
            on_click=_close_sheet,
        )

        # بناء الـ BottomSheet (v1 API)
        bs = ft.BottomSheet(
            ft.Container(
                content=ft.Column(
                    [
                        header_row,
                        ft.Divider(height=1, color=_c('card_border')),
                        filter_col,
                        ft.Container(height=10),
                        apply_btn,
                        ft.Container(height=10),  # مسافة أمان سفلية
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
        # زر مسح سريع لمربع البحث
        self._search_field.value = ""
        self._apply_filters()
        self._page.update()

    def _reset_all_filters(self, _e=None):
        # اختصار: ضغط مطوّل على زر الفلترة يمسح كل الفلاتر دفعة واحدة
        self._active_filters.clear()
        self._apply_filters()
        self._page.update()

    def handle_back(self) -> bool:
        if self._view_mode != 'list':
            self._back_to_list(None)
            return True
        return False

    def _is_rtl(self) -> bool:
        return (self._lang or '').lower() in ('ar', 'fa', 'ur')

    def _status_label(self) -> str:
        v = WikiCache.get_local_version(self._lang)
        if v == 0 and not self._entries:
            return _t('no_cache')
        return _t('up_to_date').format(v=v)

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
        self._render()
        self._page.update()

    def build(self) -> ft.Control:
        self._lang = get_current_lang() or 'en'
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
        self._apply_filters()
        self._page.update()

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

    def _rebuild_list(self):
        self._list_view.controls.clear()

        if not self._filtered:
            self._list_view.controls.append(
                ft.Container(
                    content=ft.Text(_t('no_results'), color=_c('text_dim'), size=13,
                                     text_align=ft.TextAlign.CENTER),
                    padding=40,
                    alignment=ft.Alignment(0, 0),
                )
            )
            return

        for entry in self._filtered:
            self._list_view.controls.append(self._build_card(entry))

    def _build_card(self, entry: WikiEntry) -> ft.Container:
        header_children = [
            ft.Text(entry.name, size=15, weight=ft.FontWeight.BOLD, color=_c('text')),
        ]
        if entry.category:
            header_children.append(_badge(_category_label(entry.category), _category_color(entry.category)))

        dash_btn = _ink_btn(
            content=ft.Row(
                [ft.Icon(ft.Icons.SPACE_DASHBOARD_ROUNDED, color='#FFFFFF', size=14),
                 ft.Text(_t('open_dashboard'), color='#FFFFFF', size=12)],
                spacing=6, alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=_c('accent'),
            on_click=(lambda e, en=entry: self._page.run_task(self._async_open_dash, en)),
        )

        card_buttons = [dash_btn]

        if entry.has_details:
            info_btn = _ink_btn(
                content=ft.Row(
                    [ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color='#FFFFFF', size=14),
                     ft.Text(_t('function_info'), color='#FFFFFF', size=12)],
                    spacing=6, alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor=_c('accent'),
                on_click=(lambda e, en=entry: self._page.run_task(self._async_open_detail, en)),
            )
            card_buttons.append(info_btn)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(header_children, spacing=8),
                    ft.Text(entry.desc, size=13, color=_c('text_dim'), rtl=self._is_rtl()),
                    ft.Row(card_buttons, spacing=8, expand=True),
                ],
                spacing=8,
            ),
            bgcolor=_c('card_bg'),
            border=self._card_border(),
            border_radius=12,
            padding=16,
            rtl=self._is_rtl(),
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
        color, icon_name, key, fallback = _CALLOUT_STYLES.get(kind, ('#3B82F6', _CALLOUT_DEFAULT_ICON, 'callout_note', 'Info'))
        return color, getattr(ft.Icons, icon_name, ft.Icons.INFO_OUTLINE_ROUNDED), _t(key) or fallback

    def _callout(self, title: str, text: str, color: str, icon) -> ft.Container:
        return ft.Container(content=ft.Column([ft.Row([ft.Icon(icon, color=color, size=18), ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=color)], spacing=8), ft.Text(text, size=13, color=_c('text'), rtl=self._is_rtl())], spacing=6), bgcolor=_tint(color, 24), border=ft.Border(left=ft.BorderSide(4, color)), border_radius=10, padding=12, rtl=self._is_rtl())

    def _pill(self, text: str) -> ft.Container:
        return ft.Container(content=ft.Text(text, size=12, color=_c('accent'), font_family='monospace', weight=ft.FontWeight.W_600), bgcolor=_tint(_c('accent'), 24), border_radius=6, padding=ft.Padding(10, 4, 10, 4))

    async def _async_open_dash(self, entry: WikiEntry):
        self._view_mode = 'dash'
        self._render()
        self._page.update()
        full_entry = await asyncio.get_event_loop().run_in_executor(None, WikiCache.load_entry_full, self._lang, entry.file_name)
        full_entry = full_entry or entry
        self._dash_title.value = full_entry.name
        controls = [self._rich_paragraph(full_entry.desc)]
        for b in full_entry.blocks: controls.append(self._render_dash_block(b))
        self._dash_body.controls = controls
        self._render()
        self._page.update()

    async def _async_open_detail(self, entry: WikiEntry):
        self._view_mode = 'detail'
        self._render()
        self._page.update()
        full_entry = await asyncio.get_event_loop().run_in_executor(None, WikiCache.load_entry_full, self._lang, entry.file_name)
        if not full_entry or not full_entry.details: self._back_to_list(None); return
        self._detail_title.value = f'${full_entry.name}'
        self._build_detail_body(full_entry)
        self._render()
        self._page.update()

    def _back_to_list(self, _):
        self._view_mode = 'list'
        self._render()
        self._page.update()

    def _build_detail_body(self, entry: WikiEntry):
        det = entry.details
        controls = [ft.Text(entry.desc, size=13, color=_c('text_dim')), self._code_box(det.syntax, True)]
        if det.params:
            for p in det.params:
                controls.append(ft.Container(content=ft.Column([ft.Row([ft.Text(p.name, weight='bold', color=_c('text')), _badge(p.type, '#6366F1'), _badge(p.flag, '#3B82F6')], spacing=6), ft.Text(p.desc, size=12, color=_c('text_dim'))], spacing=4), bgcolor=_c('card_bg'), border=self._card_border(), border_radius=8, padding=10))
        if det.examples:
            for ex in det.examples: controls.append(self._code_box(ex, True))
        self._detail_body.controls = controls

    def _set_busy(self, busy: bool, label: str = ''):
        self._busy = busy
        self._update_btn.opacity = 0.6 if busy else 1.0
        if label: self._status_text.value = label
        if not busy:
            self._render()
        self._page.update()

    async def _check_updates(self, e):
        # حارس: يمنع تشغيل نسختين متوازيتين لو ضغط المستخدم على الزر أكثر من مرة
        if self._busy:
            return
        self._set_busy(True, _t('checking'))

        loop = asyncio.get_event_loop()
        lang = self._lang

        try:
            remote_version = await loop.run_in_executor(None, WikiRemote.fetch_version, lang)
        except Exception as ex:
            print(f'[Wiki] fetch_version failed: {ex}')
            self._set_busy(False, _t_or_fallback('update_failed', 'فشل التحقق من التحديثات'))
            return

        local_version = WikiCache.get_local_version(lang)

        if remote_version <= local_version:
            self._set_busy(False, _t('up_to_date').format(v=local_version))
            return

        # طلب إذن الإشعارات على الموبايل (اختياري تمامًا، لا يوقف التحديث لو فشل)
        try:
            if hasattr(self._page, 'platform') and self._page.platform in [
                'android', 'ios',
                getattr(ft.PagePlatform, 'ANDROID', 'android'),
                getattr(ft.PagePlatform, 'IOS', 'ios'),
            ]:
                if hasattr(ft, 'PermissionType'):
                    self._page.request_permission(ft.PermissionType.NOTIFICATION)
        except Exception as ex:
            print(f'[Wiki] notification permission request failed: {ex}')

        self._page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, color='#FFFFFF', size=20),
                        ft.Text(_t('downloading'), color='#FFFFFF', size=14, weight=ft.FontWeight.W_600),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=_c('accent'),
                duration=4000,
            )
        )

        # شاشة تحميل بشريط تقدم فعلي تغطي جسم التاب أثناء التنزيل
        loader = LoadingScreen(container=self._root, page=self._page, title=_t('downloading'))

        async def _do_download(screen: LoadingScreen):
            index = await loop.run_in_executor(None, WikiRemote.fetch_index, lang)
            index.sort()

            total = len(index) or 1
            done_count = 0
            screen.set_progress(0.0, f'0/{total}')

            async def _fetch_one(file_name: str):
                nonlocal done_count
                text = await loop.run_in_executor(None, WikiRemote.fetch_function, lang, file_name)
                # نكتب الملف فقط هنا؛ meta.json يُعاد بناؤه مرة واحدة بعد اكتمال كل الدفعات
                # بدل قراءة/كتابة meta.json لكل ملف على حدة، لتفادي تعارض الكتابة المتزامنة
                # وتسريع العملية عمومًا
                await loop.run_in_executor(None, WikiCache.save_function_file_only, lang, file_name, text)
                done_count += 1
                screen.set_progress(done_count / total, f'{done_count}/{total}')

            # تنزيل بالتوازي على دفعات بدل ملف-بملف تسلسليًا
            chunk_size = 45
            for i in range(0, len(index), chunk_size):
                chunk = index[i:i + chunk_size]
                await asyncio.gather(*[_fetch_one(fn) for fn in chunk])
                await asyncio.sleep(0.5)

            # إعادة بناء meta.json مرة واحدة فقط لكل الملفات المحلية بعد التنزيل
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
            self._set_busy(False, _t_or_fallback('update_failed', 'فشل التحديث'))
            return

        self._entries = WikiCache.load_light_entries(lang)
        self._apply_filters()

        self._set_busy(False, _t('up_to_date').format(v=remote_version))

        self._page.show_dialog(
            ft.SnackBar(content=ft.Text(_t('up_to_date').format(v=remote_version)), duration=2500)
        )

    def load_bot(self, *_args, **_kwargs):
        self._page.run_task(self._async_load_bot_task)

    async def _async_load_bot_task(self, *args):
        self._entries = await asyncio.get_event_loop().run_in_executor(None, WikiCache.load_light_entries, self._lang)
        self._apply_filters()
        self._page.update()

    def select_events_filter(self):
        self._view_mode = 'list'
        self._active_filters = {'event'}
        self._search_field.value = ""
        self._apply_filters()
        self._render()
        if self._page:
            self._page.update()