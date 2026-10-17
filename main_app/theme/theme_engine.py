# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/theme/theme_engine.py

import weakref
import threading


# ══════════════════════════════════════════════════════════════════════════════
#  Colour helpers
# ══════════════════════════════════════════════════════════════════════════════

def _rgb(h: str) -> tuple:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _hex(rgb) -> str:
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(v))) for v in rgb)

def _mix(a: str, b: str, t: float) -> str:
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))))

def _lum(h: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def _on_color(bg: str) -> str:
    dark = '#0B0E1F'
    return '#FFFFFF' if _contrast(bg, '#FFFFFF') >= _contrast(bg, dark) else dark

def _readable(fg: str, bg: str, ratio: float = 4.5) -> str:
    for step in range(11):
        c = _mix(fg, '#FFFFFF', step * 0.07)
        if _contrast(c, bg) >= ratio:
            return c
    return '#FFFFFF'


# ══════════════════════════════════════════════════════════════════════════════
#  Theme ingredients
# ══════════════════════════════════════════════════════════════════════════════

SURFACES = {
    'midnight': {
        'name_key': 'surface_midnight', 'dark': True,
        'bg': '#11131F', 'card_bg': '#1B1E31', 'card_border': '#2B3050',
        'footer_bg': '#151829', 'input_bg': '#232744', 'input_border': '#3A4170',
        'text': '#E9ECFA', 'text_dim': '#8F98C4', 'divider': '#2B3050',
        'nav_bg': '#151829',
    },
    'amoled': {
        'name_key': 'surface_amoled', 'dark': True,
        'bg': '#000000', 'card_bg': '#0E1114', 'card_border': '#1C2228',
        'footer_bg': '#07090B', 'input_bg': '#141A1F', 'input_border': '#26313A',
        'text': '#F2F6F8', 'text_dim': '#7C8B96', 'divider': '#1C2228',
        'nav_bg': '#07090B',
    },
    'graphite': {
        'name_key': 'surface_graphite', 'dark': True,
        'bg': '#16171A', 'card_bg': '#202226', 'card_border': '#2F3238',
        'footer_bg': '#1B1C20', 'input_bg': '#26292E', 'input_border': '#3A3E46',
        'text': '#ECEDEF', 'text_dim': '#9096A0', 'divider': '#2F3238',
        'nav_bg': '#1B1C20',
    },
    'navy': {
        'name_key': 'surface_navy', 'dark': True,
        'bg': '#0D1B2A', 'card_bg': '#12243A', 'card_border': '#223A57',
        'footer_bg': '#090F18', 'input_bg': '#1A2F4A', 'input_border': '#2E4B70',
        'text': '#E6ECF5', 'text_dim': '#8796AD', 'divider': '#223A57',
        'nav_bg': '#090F18',
    },
}

ACCENTS = {
    'blurple': ('#7388D9', 'accent_blurple'),
    'sky':     ('#4A90D9', 'accent_sky'),
    'cyan':    ('#22D3EE', 'accent_cyan'),
    'emerald': ('#2DD4A0', 'accent_emerald'),
    'yellow':  ('#E6C757', 'accent_yellow'),   
    'gold':    ('#C9A227', 'accent_gold'),
    'ember':   ('#FF6A3D', 'accent_ember'),
    'violet':  ('#8B5CF6', 'accent_violet'),
}

DEFAULT_THEME  = 'midnight'
DEFAULT_ACCENT = 'blurple'
VISIBLE_THEMES = ['midnight', 'amoled', 'graphite']
HIDDEN_THEME   = 'navy'      

LEGACY_THEMES = {
    'system_da':   ('midnight', 'sky',     False),
    'v2_dark':     ('navy',     'gold',    False),
    'system_wh':   (DEFAULT_THEME, DEFAULT_ACCENT, False),
    'blue_sky':    (DEFAULT_THEME, DEFAULT_ACCENT, False),
    'yellow_bile': (DEFAULT_THEME, DEFAULT_ACCENT, False),
}

_SEMANTIC = {'success': '#3FBF86', 'danger': '#EF6A7D', 'warning': '#E6C757'}


def build_theme(surface: str, accent: str, outline: bool = False) -> dict:
    s = SURFACES.get(surface) or SURFACES[DEFAULT_THEME]
    a = (ACCENTS.get(accent) or ACCENTS[DEFAULT_ACCENT])[0]
    border       = a if outline else s['card_border']
    input_border = a if outline else s['input_border']

    return {
        'bg':             s['bg'],
        'card_bg':        s['card_bg'],
        'card_border':    border,
        'footer_bg':      s['footer_bg'],
        'popup_bg':       s['card_bg'],
        'input_bg':       s['input_bg'],
        'input_border':   input_border,
        'text':           s['text'],
        'text_dim':       s['text_dim'],
        'text_on_accent': _on_color(a),
        'accent':         a,
        'accent_hover':   _mix(a, '#FFFFFF', 0.15),
        'success':        _SEMANTIC['success'],
        'danger':         _SEMANTIC['danger'],
        'warning':        _SEMANTIC['warning'],
        'icon_bg':        s['card_border'],
        'discord':        '#5865F2',
        'github':         s['text'],
        'title_bcfd':     _readable(a, s['bg']),
        'nav_bg':         s['nav_bg'],
        'nav_active':     a,
        'nav_inactive':   s['text_dim'],
        'divider':        s['divider'],
        'online':         _SEMANTIC['success'],
        'offline':        _SEMANTIC['danger'],
        'btn_invite':     '#5865F2',
    }

ALL_THEMES = {
    key: {
        'swatch_a': ACCENTS[DEFAULT_ACCENT][0],
        'swatch_b': s['bg'],
        'data': build_theme(key, DEFAULT_ACCENT, False),
    }
    for key, s in SURFACES.items()
}


# ══════════════════════════════════════════════════════════════════════════════
#  Engine
# ══════════════════════════════════════════════════════════════════════════════

class _ThemeEngine:

    def __init__(self):
        self._subscribers: list[weakref.ref] = []
        self._current_data: dict             = {}
        self._current_key: str               = ''
        self._current_accent: str            = ''
        self._current_outline: bool          = False
        self._lock = threading.Lock()

    @property
    def themes(self) -> dict:
        return ALL_THEMES

    @property
    def surfaces(self) -> dict:
        return SURFACES

    @property
    def accents(self) -> dict:
        return ACCENTS

    @property
    def visible_keys(self) -> list:
        return list(VISIBLE_THEMES)

    @property
    def hidden_key(self):
        return HIDDEN_THEME

    @property
    def current_key(self) -> str:
        return self._current_key

    @property
    def current_accent(self) -> str:
        return self._current_accent

    @property
    def current_outline(self) -> bool:
        return self._current_outline

    def legacy(self, theme_key: str):
        return LEGACY_THEMES.get(theme_key)

    def resolve(self, theme_key: str, accent: str = None, outline: bool = None) -> tuple:
        legacy = LEGACY_THEMES.get(theme_key)
        if legacy:
            surface, acc, out = legacy
            if accent in ACCENTS:
                acc = accent
            if outline is not None:
                out = bool(outline)
            return surface, acc, out
        surface = theme_key if theme_key in SURFACES else DEFAULT_THEME
        acc = accent if accent in ACCENTS else DEFAULT_ACCENT
        return surface, acc, bool(outline)

    def preview(self, surface: str, accent: str, outline: bool = False) -> dict:
        return build_theme(surface, accent, outline)

    def info(self, theme_key: str):
        return ALL_THEMES.get(theme_key)

    def is_dark(self, theme_key: str = None) -> bool:
        s = SURFACES.get(theme_key or self._current_key)
        return True if s is None else bool(s.get('dark', True))

    def subscribe(self, callback):
        ref = (
            weakref.WeakMethod(callback)
            if hasattr(callback, '__self__')
            else weakref.ref(callback)
        )
        with self._lock:
            self._subscribers.append(ref)
            snapshot = dict(self._current_data)

        if snapshot:
            try:
                fn = ref()
                if fn:
                    fn(snapshot)
            except Exception as e:
                print(f'[ThemeEngine] subscribe notify error: {e}')

    def unsubscribe(self, callback):
        with self._lock:
            self._subscribers = [
                r for r in self._subscribers
                if r() is not None and r() != callback
            ]

    def apply(self, theme_key: str, accent: str = None, outline: bool = None):
        surface, acc, out = self.resolve(theme_key, accent, outline)
        data = build_theme(surface, acc, out)

        with self._lock:
            self._current_data    = data
            self._current_key     = surface
            self._current_accent  = acc
            self._current_outline = out

        self._notify(data)

    def _notify(self, data: dict):
        with self._lock:
            refs = list(self._subscribers)

        alive = []
        for ref in refs:
            fn = ref()
            if fn is None:
                continue
            alive.append(ref)
            try:
                fn(dict(data))
            except Exception as e:
                print(f'[ThemeEngine] subscriber error: {e}')

        with self._lock:
            self._subscribers = alive

    # ── Color accessors ───────────────────────────────────────────────────────

    def hex(self, key: str, fallback: str = '#888888') -> str:
        return self._current_data.get(key, fallback)

    def color(self, key: str, fallback: str = '#888888') -> str:
        return self.hex(key, fallback)

    def __getitem__(self, key: str) -> str:
        return self.hex(key)

    def __contains__(self, key: str) -> bool:
        return key in self._current_data

    @property
    def data(self) -> dict:
        with self._lock:
            return dict(self._current_data)

    @property
    def loaded(self) -> bool:
        return bool(self._current_data)


ThemeEngine = _ThemeEngine()