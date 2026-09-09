# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/load/loading_view.py — Generic full-view loading screen (Flet 0.85.2+ / v1 API)

import asyncio
import random

import flet as ft

from main_app.theme.theme_engine import ThemeEngine


def _c(key: str) -> str:
    return ThemeEngine.hex(key)


class LoadingScreen:

    BAR_WIDTH = 260

    def __init__(self, container: ft.Container = None, page: ft.Page = None, title: str = ''):
        self._container = container
        self._page = page

        self._bar_fill = ft.Container(
            width=0, height=8, border_radius=4, bgcolor=_c('accent'),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        self._bar_track = ft.Container(
            width=self.BAR_WIDTH, height=8, border_radius=4,
            bgcolor=_c('card_border'),
            content=ft.Row([self._bar_fill], spacing=0),
        )

        self._percent_text = ft.Text('0%', size=12, color=_c('accent'), weight=ft.FontWeight.W_600)
        self._status_text = ft.Text('', size=13, color=_c('text_dim'))
        self._title_text = ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=_c('text'))

        self._inner_content = ft.Column(
            [
                ft.ProgressRing(width=36, height=36, color=_c('accent'), stroke_width=3),
                self._title_text,
                self._bar_track,
                ft.Row(
                    [self._status_text, self._percent_text],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        self._view = ft.Container(
            content=self._inner_content,
            alignment=ft.Alignment(0, 0),
            expand=True,
            bgcolor=_c('bg'),          
        )

    def set_progress(self, fraction: float, status: str = '') -> None:
        fraction = max(0.0, min(1.0, fraction))
        self._bar_fill.width = self.BAR_WIDTH * fraction
        self._percent_text.value = f'{int(fraction * 100)}%'
        if status:
            self._status_text.value = status
        if self._page:
            self._page.update()

    async def run(self, work_coro, done_message: str = '',
                   extra_hold_min: float = 1.0, extra_hold_max: float = 3.0):
        """
        يستبدل محتوى الـ container بالكامل.
        جيد عندما يكون الـ container يغطي الشاشة أصلاً.
        """
        if self._container is None:
            raise ValueError('LoadingScreen requires a container for run()')

        previous_content = self._container.content
        previous_bg = getattr(self._container, 'bgcolor', None)

        # نجعل الـ container نفسه يغطي الشاشة بالكامل
        self._container.content = self._view
        self._container.bgcolor = _c('bg')
        self._container.expand = True
        self._container.alignment = ft.Alignment(0, 0)
        self._page.update()

        result = None
        error: Exception | None = None
        try:
            result = await work_coro(self)
        except Exception as e:
            error = e

        if error is None:
            self.set_progress(1.0, done_message or self._status_text.value)
            lo = max(0.0, extra_hold_min)
            hi = max(lo, min(3.0, extra_hold_max))
            extra = random.uniform(lo, hi)
            if extra > 0:
                await asyncio.sleep(extra)

        # استعادة الحالة السابقة
        self._container.content = previous_content
        self._container.bgcolor = previous_bg
        self._page.update()

        if error is not None:
            raise error
        return result

    async def run_overlay(self, work_coro, done_message: str = '',
                           extra_hold_min: float = 1.0, extra_hold_max: float = 3.0):
        """
        أفضل طريقة لتغطية الشاشة بالكامل (خاصة على الـ APK).
        تستخدم page.overlay + Container يتمدد على كل الشاشة.
        """
        # نبني overlay يغطي الشاشة 100%
        overlay = ft.Container(
            content=self._view,
            alignment=ft.Alignment(0, 0),
            expand=True,
            bgcolor=_c('bg'),
            # هذه الخصائص تساعد في تغطية الشاشة على الموبايل
            width=self._page.width if self._page.width else None,
            height=self._page.height if self._page.height else None,
            left=0,
            top=0,
            right=0,
            bottom=0,
        )

        self._page.overlay.append(overlay)
        self._page.update()

        result = None
        error: Exception | None = None
        try:
            result = await work_coro(self)
        except Exception as e:
            error = e

        if error is None:
            self.set_progress(1.0, done_message or self._status_text.value)
            lo = max(0.0, extra_hold_min)
            hi = max(lo, min(3.0, extra_hold_max))
            extra = random.uniform(lo, hi)
            if extra > 0:
                await asyncio.sleep(extra)

        if overlay in self._page.overlay:
            self._page.overlay.remove(overlay)
        self._page.update()

        if error is not None:
            raise error
        return result