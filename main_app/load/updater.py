# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/load/updater.py

import re
import json
import asyncio
import platform as _platform_mod
import urllib.request

import flet as ft

from main_app.theme.theme_engine import ThemeEngine
from main_app.langs.translations import Translations
from main_app.settings import get_current_lang


def _t(key: str, fallback: str = '') -> str:
    val = Translations.get(key, get_current_lang())
    return val if val and val != key else fallback


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


# ── Config ───────────────────────────────────────────────────────────

APP_VERSION = "2.4.1"
GITHUB_REPO = "obgwew/FDSB"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

ASSET_EXTENSION = {
    'windows': '.exe',
    'android': '.apk',
    'macos':   '.dmg',
    'linux':   '.appimage',
}


# ── Version compare ──────────────────────────────────────────────────

def _parse_version(v: str) -> tuple:
    v = (v or '').strip().lstrip('vV')
    parts = re.findall(r'\d+', v)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


# ── GitHub API ───────────────────────────────────────────────────────

def _fetch_latest_release() -> dict | None:
    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'FDSB-UpdateChecker',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[Updater] fetch failed: {e}')
        return None


def _select_asset(assets: list, plat: str) -> dict | None:
    ext = ASSET_EXTENSION.get(plat)
    if not ext:
        return None

    candidates = [a for a in assets if a.get('name', '').lower().endswith(ext)]
    if not candidates:
        return None

    if plat == 'android' and len(candidates) > 1:
        machine = _platform_mod.machine().lower()
        wants_64 = any(k in machine for k in ('64', 'aarch64', 'arm64'))
        for a in candidates:
            name = a['name'].lower()
            if wants_64 and ('arm64' in name or 'v8a' in name):
                return a
        for a in candidates:
            name = a['name'].lower()
            if not wants_64 and ('armeabi' in name or 'v7a' in name):
                return a

    return candidates[0]


# ── Update dialog ────────────────────────────────────────────────────

class UpdateOverlay:

    def __init__(self, page: ft.Page, release: dict, asset: dict):
        self._page    = page
        self._release = release
        self._asset   = asset

        changelog = (release.get('body') or '').strip()
        if len(changelog) > 500:
            changelog = changelog[:500] + '…'

        self._later_btn = ft.TextButton(
            content=ft.Text(_t('app_update_later', 'Later'), color=_c('text_dim')),
            on_click=self._on_later,
        )
        self._update_btn = ft.FilledButton(
            content=ft.Text(_t('app_update_now', 'Update Now'), color='#FFFFFF', weight=ft.FontWeight.W_600),
            on_click=self._on_update,
            style=ft.ButtonStyle(
                bgcolor=_c('accent'),
                color='#FFFFFF',
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

        self._dlg = ft.AlertDialog(
            modal=False,
            bgcolor=_c('popup_bg'),
            shape=ft.RoundedRectangleBorder(radius=18),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SYSTEM_UPDATE_ROUNDED, color=_c('accent')),
                    ft.Text(_t('app_update_title', 'Update Available'),
                            weight=ft.FontWeight.BOLD, color=_c('text')),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    ft.Text(
                        f"{_t('app_update_new_version', 'New Version')}: {release.get('tag_name', '')}"
                        f"   ({_t('app_update_current_version', 'Current')}: {APP_VERSION})",
                        size=13, color=_c('text'),
                    ),
                    ft.Container(
                        content=ft.Text(
                            changelog or _t('app_update_no_changelog', 'No changelog available for this update.'),
                            size=12, color=_c('text_dim'),
                        ),
                        padding=ft.Padding(top=6, bottom=6, left=0, right=0),
                    ),
                ],
                tight=True,
                spacing=4,
                width=320,
            ),
            actions=[self._later_btn, self._update_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def show(self):
        self._page.show_dialog(self._dlg)

    def _on_later(self, _):
        self._page.pop_dialog()

    async def _open_download(self, url: str):
        await self._page.launch_url(url)

    def _on_update(self, _):
        self._page.run_task(self._open_download, self._asset['browser_download_url'])
        self._page.pop_dialog()


# ── Entry point ──────────────────────────────────────────────────────

async def check_for_updates(page: ft.Page, app_data_dir: str, plat: str):
    loop = asyncio.get_event_loop()
    release = await loop.run_in_executor(None, _fetch_latest_release)

    if not release or release.get('draft') or release.get('prerelease'):
        return

    tag = release.get('tag_name', '')
    if not tag or not is_newer(tag, APP_VERSION):
        return

    asset = _select_asset(release.get('assets', []), plat)
    if not asset:
        print(f'[Updater] no matching asset for platform "{plat}"')
        return

    UpdateOverlay(page, release, asset).show()