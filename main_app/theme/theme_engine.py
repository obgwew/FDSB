# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/theme_engine.py

import weakref
import threading


class _ThemeEngine:

    def __init__(self):
        self._subscribers: list[weakref.ref] = []
        self._current_data: dict             = {}
        self._lock = threading.Lock()

    # ── Subscribe / Unsubscribe ───────────────────────────────────────────────

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
                if r() is not None and r() is not callback
            ]

    # ── Apply ─────────────────────────────────────────────────────────────────

    def apply(self, theme_key: str, all_themes: dict):
        if theme_key not in all_themes:
            theme_key = 'system'

        data = dict(all_themes[theme_key]['data'])

        with self._lock:
            self._current_data = data

        self._notify(data)

    # ── Notify ────────────────────────────────────────────────────────────────

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

    # ── Data snapshot ─────────────────────────────────────────────────────────

    @property
    def data(self) -> dict:
        with self._lock:
            return dict(self._current_data)

    @property
    def loaded(self) -> bool:
        return bool(self._current_data)


ThemeEngine = _ThemeEngine()