# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/settings_app.py . migrated to Flet 0.85.2+ / v1 API u

import os
import sys
import json
import base64
import weakref

import flet as ft

from main_app.langs._translations import Translations
from main_app.theme.theme_engine import ThemeEngine, DEFAULT_THEME


# ══════════════════════════════════════════════════════════════════════════════
#  Platform & storage
# ══════════════════════════════════════════════════════════════════════════════

APP_VERSION = "v2.5.0"

def _get_app_icon_b64() -> str | None:
    current_dir  = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    search_dirs = []
    for folder in ('icons', 'icon'):
        search_dirs += [
            os.path.join(current_dir, folder),
            os.path.join(project_root, 'main_app', folder),
            os.path.join(project_root, folder),
            os.path.join(os.getcwd(), 'main_app', folder),
        ]

    exts  = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
    names = ('fdsb', 'icon', 'logo')

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        files = os.listdir(d)

        for n in names:
            for f in files:
                stem, ext = os.path.splitext(f)
                if stem.lower() == n and ext.lower() in exts:
                    return _read_b64(os.path.join(d, f))

        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                return _read_b64(os.path.join(d, f))

    print('[Settings] app icon not found in:', search_dirs)
    return None


def _read_b64(path: str) -> str | None:
    try:
        with open(path, 'rb') as fh:
            return base64.b64encode(fh.read()).decode('ascii')
    except Exception as e:
        print(f'[Settings] icon read failed ({path}): {e}')
        return None
    
    current_dir  = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    search_dirs = [
        os.path.join(current_dir, 'icon'),
        os.path.join(project_root, 'main_app', 'icon'),
        os.path.join(project_root, 'icon'),
        os.path.join(os.getcwd(), 'main_app', 'icon'),
    ]
    names = ('fdsb.png')

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower() in names:
                try:
                    with open(os.path.join(d, f), 'rb') as fh:
                        return base64.b64encode(fh.read()).decode('ascii')
                except Exception as e:
                    print(f'[Settings] icon read failed: {e}')

    print('[Settings] app icon not found in:', search_dirs)
    return None

def _get_app_version() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fname in ('version.json', 'version.txt'):
        p = os.path.join(base_dir, fname)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    if fname.endswith('.json'):
                        return str(json.load(f).get('version', APP_VERSION))
                    return f.read().strip() or APP_VERSION
            except Exception:
                pass
    return APP_VERSION

def is_mobile() -> bool:
    return os.getenv('FLET_PLATFORM', '').lower() in ('android', 'ios')

def get_persistent_base_dir() -> str:
    storage_data = os.getenv('FLET_APP_STORAGE_DATA')
    if storage_data:
        return storage_data
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_app_data_dir() -> str:
    path = os.path.join(get_persistent_base_dir(), 'app_data')
    os.makedirs(path, exist_ok=True)
    return path

_SETTINGS_PATH = os.path.join(get_app_data_dir(), 'settings.json')

def load_settings() -> dict:
    try:
        with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(patch: dict):
    data = load_settings()
    data.update(patch)
    try:
        with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Settings] save failed: {e}')

def _saved_theme() -> tuple:
    d     = load_settings()
    style = d.get('_style') or {}
    return ThemeEngine.resolve(d.get('theme', DEFAULT_THEME),
                               style.get('accent'), style.get('outline'))

def get_current_theme() -> str:
    return _saved_theme()[0]

def get_current_accent() -> str:
    return _saved_theme()[1]

def get_current_outline() -> bool:
    return _saved_theme()[2]

def get_current_lang() -> str:
    return (load_settings().get('lang', 'en') or 'en').lstrip('_') or 'en'

_LANG_DETAILS: dict[str, dict[str, str]] = {
    'ar': {'name': 'العربية',  'sub': 'Arabic',    'code': 'AR'},
    'en': {'name': 'English',  'sub': 'English',   'code': 'EN'},
    'fa': {'name': 'فارسی',    'sub': 'Persian',   'code': 'FA'},
    'ur': {'name': 'اردو',     'sub': 'Urdu',      'code': 'UR'},
    'fr': {'name': 'Français', 'sub': 'French',    'code': 'FR'},
    'de': {'name': 'Deutsch',  'sub': 'German',    'code': 'DE'},
    'tr': {'name': 'Türkçe',   'sub': 'Turkish',   'code': 'TR'},
    'ch': {'name': '中文',     'sub': 'Chinese',   'code': 'ZH'},
    'ru': {'name': 'Русский',  'sub': 'Russian',   'code': 'RU'},
    'pl': {'name': 'Polski',   'sub': 'Polish',    'code': 'PL'},
    'es': {'name': 'Español',  'sub': 'Spanish',   'code': 'ES'},
    'id': {'name': 'Bahasa Indonesia', 'sub': 'Indonesian', 'code': 'ID'},
    'ja': {'name': '日本語',   'sub': 'Japanese',  'code': 'JA'},
    'hi': {'name': 'हिंदी',    'sub': 'Hindi',     'code': 'HI'},
}

def available_languages() -> list:
    return [k.lstrip('_') for k in Translations.translations.keys()]

def language_info(code: str) -> dict:
    return _LANG_DETAILS.get(code, {'name': code.upper(), 'sub': code, 'code': code.upper()})

def _t(key: str) -> str:
    return Translations.get(key, get_current_lang())

_lang_listeners: list = []

def subscribe_language(callback):
    ref = (weakref.WeakMethod(callback) if hasattr(callback, '__self__')
           else weakref.ref(callback))
    _lang_listeners.append(ref)

def unsubscribe_language(callback):
    _lang_listeners[:] = [r for r in _lang_listeners
                          if r() is not None and r() != callback]

def set_language(code: str) -> bool:
    if not code or code == get_current_lang():
        return False
    save_settings({'lang': code})
    alive = []
    for ref in list(_lang_listeners):
        fn = ref()
        if fn is None:
            continue
        alive.append(ref)
        try:
            fn(code)
        except Exception as e:
            print(f'[Settings] language listener error: {e}')
    _lang_listeners[:] = alive
    return True

def _ensure_theme_loaded():
    if not ThemeEngine.loaded:
        ThemeEngine.apply(*_saved_theme())

def theme_hex(key: str, fallback: str = '#888888') -> str:
    _ensure_theme_loaded()
    return ThemeEngine.hex(key, fallback)

def _c(key: str) -> str:
    return theme_hex(key)

def theme_data() -> dict:
    _ensure_theme_loaded()
    return ThemeEngine.data

def theme_loaded() -> bool:
    return ThemeEngine.loaded

def subscribe_theme(callback):
    _ensure_theme_loaded()
    ThemeEngine.subscribe(callback)

def unsubscribe_theme(callback):
    ThemeEngine.unsubscribe(callback)

def is_dark_theme(theme_key: str = None) -> bool:
    return ThemeEngine.is_dark(theme_key or get_current_theme())

def list_themes() -> list:
    return ThemeEngine.visible_keys

def list_accents() -> list:
    return [(k, v[0], v[1]) for k, v in ThemeEngine.accents.items()]

def preview_theme(surface: str, accent: str, outline: bool = False) -> dict:
    return ThemeEngine.preview(surface, accent, outline)

def get_theme_info(theme_key: str):
    return ThemeEngine.info(theme_key)

def init_theme():
    ThemeEngine.apply(*_saved_theme())

def apply_page_theme(page: ft.Page):
    page.bgcolor = theme_hex('bg')
    page.theme_mode = ft.ThemeMode.DARK if is_dark_theme() else ft.ThemeMode.LIGHT

def apply_theme_globally(theme_key: str, accent: str = None, outline: bool = None):
    cur_surface, cur_accent, cur_outline = _saved_theme()
    surface, acc, out = ThemeEngine.resolve(
        theme_key, accent or cur_accent, cur_outline if outline is None else outline)

    ThemeEngine.apply(surface, acc, out)

    save_settings({
        'theme':  surface,
        '_style': {'accent': acc, 'outline': out},
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Shared UI helpers (also imported by settings_bot.py)
# ══════════════════════════════════════════════════════════════════════════════

def _border_all(w: float, color: str) -> ft.Border:
    s = ft.BorderSide(w, color)
    return ft.Border(left=s, top=s, right=s, bottom=s)

def _soft_shadow(blur: int = 16, dy: int = 6, opacity: float = 0.10) -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=blur,
        color=ft.Colors.with_opacity(opacity, '#000000'),
        offset=ft.Offset(0, dy),
    )

def _card_container(content: ft.Control) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=_c('card_bg'),
        border=_border_all(1, _c('card_border')),
        border_radius=14,
        padding=ft.Padding(left=16, top=14, right=16, bottom=14),
        shadow=_soft_shadow(),
    )

def _icon_chip(icon: str, bgcolor: str = None, icon_color: str = None,
               size: int = 30) -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, size=15, color=icon_color or '#FFFFFF'),
        width=size, height=size,
        border_radius=size * 0.34,
        bgcolor=bgcolor or _c('accent'),
        alignment=ft.Alignment(0, 0),
    )

def _section_title(text: str, icon: str = None) -> ft.Control:
    if not icon:
        return ft.Text(text, size=12, weight=ft.FontWeight.BOLD, color=_c('text_dim'))
    return ft.Row(
        [
            _icon_chip(icon, bgcolor=_c('bg'), icon_color=_c('accent'), size=24),
            ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=_c('text')),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Settings screen
# ══════════════════════════════════════════════════════════════════════════════

class SettingsAppScreen:

    def __init__(self, page: ft.Page, on_back: callable,
                 on_lang_change=None, on_theme_change=None):
        self._page            = page
        self._on_back         = on_back
        self._on_lang_change  = on_lang_change
        self._on_theme_change = on_theme_change

        self._lang          = get_current_lang()
        self._current_theme   = get_current_theme()
        self._current_accent  = get_current_accent()
        self._current_outline = get_current_outline()
        self._is_committing = False
        self._root: ft.Column | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_header(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_color=_c('text'),
                        on_click=lambda _: self._on_back(),
                    ),
                    ft.Text(
                        _t('tab_settings'),
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=_c('title_bcfd'),
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=8, top=10, right=18, bottom=10),
        )

    def _build_app_info(self) -> ft.Control:
        icon_b64    = _get_app_icon_b64()
        version_str = _get_app_version()

        fallback = ft.Container(
            content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=36, color=_c('accent')),
            width=64,
            height=64,
            alignment=ft.Alignment(0, 0),
        )

        img_control = (
            ft.Image(
                src=icon_b64,
                width=64,
                height=64,
                fit=ft.BoxFit.CONTAIN,
                border_radius=16,
                error_content=fallback,
            )
            if icon_b64 else fallback
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=img_control,
                        width=64,
                        height=64,
                        border_radius=16,
                        shadow=_soft_shadow(blur=16, dy=6, opacity=0.20),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                _t('main_title'),
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=_c('text'),
                            ),
                            ft.Container(
                                content=ft.Text(
                                    f"v{version_str.lstrip('v')}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=_c('accent'),
                                ),
                                bgcolor=_c('accent') + '1A',
                                border_radius=6,
                                padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                            ),
                        ],
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(top=8, bottom=4, left=0, right=0),
        )

    def _build_body(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    self._build_app_info(),
                    self._build_language_section(),
                    self._build_design_section(),
                    ft.Container(height=24),
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=ft.Padding(left=16, top=8, right=16, bottom=0),
            expand=True,
        )

    def build(self) -> ft.Control:
        self._root = ft.Column(
            [self._build_header(), self._build_body()],
            spacing=0,
            expand=True,
        )
        return self._root

    def _rebuild(self):
        if self._root is None:
            return
        self._root.controls = [self._build_header(), self._build_body()]
        self._page.update()

    # ── Language ──────────────────────────────────────────────────────────────

    def _build_language_section(self) -> ft.Control:
        return ft.Column(
            [
                _section_title(_t('general_section'), ft.Icons.TUNE_ROUNDED),
                _card_container(
                    ft.Row(
                        [
                            ft.Text(
                                _t('language'),
                                size=13,
                                color=_c('text'),
                                expand=True,
                                weight=ft.FontWeight.W_500,
                            ),
                            self._build_lang_button(),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=8,
        )

    def _build_lang_button(self) -> ft.Control:
        info = language_info(self._lang)

        code_badge = ft.Container(
            content=ft.Text(
                info['code'],
                size=11,
                weight=ft.FontWeight.BOLD,
                color=_c('accent'),
            ),
            bgcolor=_c('accent') + '22',
            border_radius=6,
            padding=ft.Padding(left=6, top=2, right=6, bottom=2),
        )

        return ft.Container(
            content=ft.Row(
                [
                    _icon_chip(ft.Icons.TRANSLATE_ROUNDED, bgcolor=_c('bg'), icon_color=_c('accent'), size=24),
                    ft.Text(info['name'], size=13, weight=ft.FontWeight.BOLD, color=_c('text')),
                    code_badge,
                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=18, color=_c('text_dim')),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=_c('input_bg'),
            border=_border_all(1, _c('input_border')),
            border_radius=10,
            padding=ft.Padding(left=10, top=6, right=8, bottom=6),
            ink=True,
            on_click=lambda _: self._open_lang_modal(),
        )

    def _open_lang_modal(self):
        available_codes = available_languages()
        languages_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        def _select_lang(code: str):
            self._page.pop_dialog()
            self._page.run_task(self._apply_language, code)

        def _populate_languages(filter_query: str = ''):
            languages_col.controls.clear()
            q = filter_query.strip().lower()

            for code in available_codes:
                info = language_info(code)
                name = info['name']
                sub  = info.get('sub', '')

                if q and (q not in name.lower() and q not in sub.lower() and q not in code.lower()):
                    continue

                is_active = (code == self._lang)

                code_badge = ft.Container(
                    content=ft.Text(
                        info['code'],
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=_c('accent') if is_active else _c('text_dim'),
                    ),
                    bgcolor=_c('accent') + '22' if is_active else _c('card_border'),
                    border_radius=6,
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                )

                trailing_icon = ft.Icon(
                    ft.Icons.CHECK_CIRCLE_ROUNDED if is_active else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                    size=18,
                    color=_c('accent') if is_active else _c('card_border'),
                )

                row = ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Row([ft.Text(name, size=13, weight=ft.FontWeight.BOLD, color=_c('text')), code_badge], spacing=6),
                                    ft.Text(sub, size=11, color=_c('text_dim')) if sub else ft.Container(),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            trailing_icon,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=_c('accent') + '15' if is_active else _c('card_bg'),
                    border=_border_all(1, _c('accent') if is_active else _c('card_border')),
                    border_radius=10,
                    padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                    ink=True,
                    on_click=lambda _, c=code: _select_lang(c),
                )
                languages_col.controls.append(row)

            if not languages_col.controls:
                languages_col.controls.append(
                    ft.Container(
                        content=ft.Text(_t('no_languages_found'), color=_c('text_dim'), size=12),
                        alignment=ft.Alignment(0, 0),
                        padding=20,
                    )
                )

        _populate_languages()

        search_field = ft.TextField(
            hint_text=_t('search_lang'),
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            dense=True,
            border_color=_c('card_border'),
            focused_border_color=_c('accent'),
            cursor_color=_c('accent'),
            text_style=ft.TextStyle(color=_c('text'), size=13),
            bgcolor=_c('input_bg'),
            border_radius=10,
            content_padding=ft.Padding(left=8, right=8, top=0, bottom=0),
            on_change=lambda e: (_populate_languages(e.control.value), self._page.update()),
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Row(
                [
                    _icon_chip(ft.Icons.LANGUAGE_ROUNDED, bgcolor=_c('bg'), icon_color=_c('accent'), size=28),
                    ft.Text(_t('select_language'), weight=ft.FontWeight.BOLD, size=15, color=_c('text')),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        search_field,
                        ft.Container(
                            content=languages_col,
                            expand=True,
                            padding=ft.Padding(top=6, bottom=0, left=0, right=0),
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=380,
                height=420,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text(_t('cancel'), color=_c('text_dim')),
                    on_click=lambda _: self._page.pop_dialog(),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._page.show_dialog(dlg)

    async def _apply_language(self, selected: str):
        if not selected or selected == self._lang:
            return
        from main_app.load.loading_view import LoadingScreen

        set_language(selected)
        self._lang = selected

        async def _apply(ls: 'LoadingScreen'):
            ls.set_progress(0.3, _t('language'))
            if self._on_lang_change:
                try:
                    self._on_lang_change(selected)
                except Exception as e:
                    print(f'[Settings] on_lang_change failed: {e}')
            ls.set_progress(0.7, _t('language'))
            self._rebuild()
            ls.set_progress(1.0, _t('language'))

        ls = LoadingScreen(page=self._page, title=_t('language'))
        await ls.run_overlay(_apply)

    # ── Design: style x accent x borders ──────────────────────────────────────

    def _build_design_section(self) -> ft.Control:
        surfaces = list(list_themes())
        hidden   = ThemeEngine.hidden_key
        if hidden and hidden not in surfaces:
            surfaces.append(hidden)

        acc_name = next((n for k, _h, n in list_accents() if k == self._current_accent), '')

        return ft.Column(
            [
                _section_title(_t('design_section'), ft.Icons.PALETTE_OUTLINED),
                _card_container(
                    ft.Column(
                        [
                            ft.Text(_t('theme_style'), size=12,
                                    weight=ft.FontWeight.BOLD, color=_c('text_dim')),
                            *[self._surface_row(k) for k in surfaces],
                            ft.Divider(color=_c('divider'), height=1),
                            ft.Row(
                                [
                                    ft.Text(_t('accent_color'), size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=_c('text_dim'), expand=True),
                                    ft.Text(_t(acc_name) if acc_name else '', size=12,
                                            color=_c('text')),
                                ],
                            ),
                            self._accent_picker(),
                            ft.Divider(color=_c('divider'), height=1),
                            self._outline_row(),
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=8,
        )

    def _surface_row(self, surface_key: str) -> ft.Control:
        is_sel = surface_key == self._current_theme
        prev   = preview_theme(surface_key, self._current_accent, self._current_outline)
        colors = [prev['bg'], prev['card_bg'], prev['accent']]

        swatch = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=18, height=34, bgcolor=col,
                        border_radius=ft.BorderRadius(
                            top_left=8 if i == 0 else 0,
                            bottom_left=8 if i == 0 else 0,
                            top_right=8 if i == len(colors) - 1 else 0,
                            bottom_right=8 if i == len(colors) - 1 else 0,
                        ),
                    )
                    for i, col in enumerate(colors)
                ],
                spacing=0,
            ),
            border=_border_all(1, _c('card_border')),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            width=18 * len(colors),
            height=34,
            shadow=_soft_shadow(blur=8, dy=3, opacity=0.14),
        )

        return ft.Container(
            content=ft.Row(
                [
                    swatch,
                    ft.Text(
                        _t(ThemeEngine.surfaces[surface_key]['name_key']),
                        size=13, color=_c('text'),
                        weight=ft.FontWeight.W_500, expand=True,
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_ROUNDED if is_sel
                        else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                        size=20,
                        color=_c('accent') if is_sel else _c('card_border'),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=56,
            border_radius=12,
            bgcolor=_c('accent') + '18' if is_sel else 'transparent',
            border=_border_all(1, _c('accent')) if is_sel else None,
            padding=ft.Padding(left=8, right=12, top=0, bottom=0),
            ink=True,
            on_click=lambda _, k=surface_key: self._page.run_task(self._commit_theme, k, None, None),
        )

    def _accent_picker(self) -> ft.Control:
        circles = []
        for key, hex_, name_key in list_accents():
            is_sel = key == self._current_accent
            on_col = preview_theme(self._current_theme, key, False)['text_on_accent']
            circles.append(
                ft.Container(
                    content=ft.Icon(ft.Icons.CHECK_ROUNDED, size=20, color=on_col) if is_sel else None,
                    width=40, height=40, border_radius=20,
                    bgcolor=hex_,
                    alignment=ft.Alignment(0, 0),
                    border=_border_all(3, _c('text')) if is_sel else _border_all(1, _c('card_border')),
                    tooltip=_t(name_key),
                    ink=True,
                    on_click=lambda _, k=key: self._page.run_task(self._commit_theme, None, k, None),
                )
            )
        return ft.Row(circles, wrap=True, spacing=10, run_spacing=10)

    def _outline_row(self) -> ft.Control:
        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(_t('accent_borders'), size=13, color=_c('text'),
                                weight=ft.FontWeight.W_500),
                        ft.Text(_t('accent_borders_desc'), size=11, color=_c('text_dim')),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Switch(
                    value=self._current_outline,
                    active_color=_c('accent'),
                    on_change=lambda e: self._page.run_task(
                        self._commit_theme, None, None, bool(e.control.value)),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    async def _commit_theme(self, surface=None, accent=None, outline=None):
        if self._is_committing:
            return
        surface = surface or self._current_theme
        accent  = accent  or self._current_accent
        outline = self._current_outline if outline is None else bool(outline)
        if (surface, accent, outline) == (
                self._current_theme, self._current_accent, self._current_outline):
            return

        self._is_committing = True
        try:
            from main_app.load.loading_view import LoadingScreen

            async def _apply(ls: 'LoadingScreen'):
                ls.set_progress(0.3, _t('design_section'))

                apply_theme_globally(surface, accent, outline)
                self._current_theme   = surface
                self._current_accent  = accent
                self._current_outline = outline
                apply_page_theme(self._page)

                ls.set_progress(0.6, _t('design_section'))

                if self._on_theme_change:
                    try:
                        self._on_theme_change(surface)
                    except Exception as e:
                        print(f'[Settings] on_theme_change failed: {e}')

                self._rebuild()
                ls.set_progress(1.0, _t('design_section'))

            ls = LoadingScreen(page=self._page, title=_t('design_section'))
            await ls.run_overlay(_apply)
        finally:
            self._is_committing = False