# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
# main_app/motion.py . fast slide transitions + swipe-to-navigate (Flet 0.85.x / v1 compatible)

import asyncio
import itertools
import math
import threading
import flet as ft

# ─────────────────────────────  tuning knobs  ─────────────────────────────

SLIDE_MS          = 220                     # مدة حركة الانزلاق بالمللي ثانية
SLIDE_CURVE       = ft.AnimationCurve.EASE_OUT_CUBIC

SWIPE_ENABLED     = True                    # تفعيل السحب للتنقل
SWIPE_ALLOW_MOUSE = True                    # دعم السحب بالفأرة أيضاً
DRAG_INTERVAL_MS  = 16                      # معدل تحديث حركة السحب
DEAD_ZONE_PX      = 12                      # منطقة الموت لتفادي اللمسات العرضية
COMMIT_FRACTION   = 0.25                    # نسبة السحب المطلوبة لتأكيد التبديل
FLING_VELOCITY    = 500.0                   # سرعة النفضة السريعة للتبديل
FLING_MIN_PX      = 25.0

# ──────────────────────────────────────────────────────────────────────────

_ids = itertools.count(1)


def _instant_anim() -> ft.Animation:
    return ft.Animation(duration=0, curve=ft.AnimationCurve.LINEAR)


class SlideStack:
    """
    يعرض واجهة واحدة في كل مرة مع حركة انزلاق أفقية سلسة (Slide Animation)،
    متوافق تماماً مع Flet 0.85+ بدون مشاكل تجميد العناصر.
    """

    def __init__(self, page: ft.Page, duration: int = SLIDE_MS):
        self._page     = page
        self._duration = int(duration)
        self._lock     = threading.RLock()
        self._timer    = None
        self._gen      = 0
        self._cur      = None
        self._other    = None
        self._side     = 0
        self._dragging = False

        # Stack أساسي يحوي الطبقات المعروضة
        self.control = ft.Stack(
            [], expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

    @staticmethod
    def make_slot(content: ft.Control, key: str = None) -> ft.Container:
        """
        إنشاء حاوية جديدة مجهزة للأنيميشن.
        """
        # في Flet v1 لا نضع key إجباري على الحاوية لتفادي التجميد
        return ft.Container(
            content=content,
            key=key,
            left=0, top=0, right=0, bottom=0,
            expand=True,
            offset=ft.Offset(0, 0),
            animate_offset=_instant_anim(),
        )

    def _anim(self) -> ft.Animation:
        return ft.Animation(duration=self._duration, curve=SLIDE_CURVE)

    def _push(self, *controls):
        valid = [c for c in controls if c is not None]
        try:
            if valid:
                self._page.update(*valid)
            else:
                self._page.update(self.control)
        except Exception:
            try:
                self._page.update()
            except Exception:
                pass

    def _cancel_timer(self):
        self._gen += 1
        t, self._timer = self._timer, None
        if t is not None:
            try:
                t.cancel()
            except Exception:
                pass

    def _start_timer(self, delay: float, fn):
        self._cancel_timer()
        gen = self._gen

        async def _run():
            await asyncio.sleep(delay)
            if gen != self._gen:
                return
            self._timer = None
            try:
                fn()
            except Exception as ex:
                pass

        try:
            self._timer = self._page.run_task(_run)
        except Exception:
            t = threading.Timer(delay, lambda: fn() if gen == self._gen else None)
            t.daemon = True
            self._timer = t
            t.start()

    def _finish_locked(self):
        self._cancel_timer()
        if self._cur is None:
            return
        self._other    = None
        self._dragging = False
        try:
            self._cur.animate_offset = _instant_anim()
            self._cur.offset = ft.Offset(0, 0)
        except Exception:
            pass
        self.control.controls = [self._cur]

    def _finish(self):
        with self._lock:
            self._finish_locked()
            self._push()

    # ── التبديل البرمجي مع أنيميشن الانزلاق ──────────────────────────

    def show(self, content: ft.Control, direction: int = 0, push: bool = True):
        with self._lock:
            if self._cur is not None and getattr(self._cur, 'content', None) is content:
                if push:
                    self._push()
                return
        self.show_slot(self.make_slot(content), direction, push)

    def show_slot(self, slot: ft.Container, direction: int = 0, push: bool = True):
        with self._lock:
            self._finish_locked()
            cur = self._cur

            if cur is slot:
                if push:
                    self._push()
                return

            # حالة البداية أو بدون أنيميشن
            if cur is None or direction == 0:
                try:
                    slot.animate_offset = _instant_anim()
                    slot.offset = ft.Offset(0, 0)
                except Exception:
                    pass
                self._cur = slot
                self.control.controls = [slot]
                if push:
                    self._push()
                return

            # تجهيز أنيميشن الانزلاق:
            # 1. وضع الشاشة الجديدة خارج مجال الرؤية بناءً على الاتجاه (يمين أو يسار)
            try:
                slot.animate_offset = _instant_anim()
                slot.offset = ft.Offset(float(direction), 0.0)
            except Exception:
                # إذا كانت الحاوية مجمدة من Flet، نغلف محتواها في حاوية جديدة تماماً
                slot = self.make_slot(slot.content)
                slot.offset = ft.Offset(float(direction), 0.0)

            self.control.controls = [cur, slot]
            self._cur = slot
            self._push()

            # 2. إطلاق أنيميشن الانزلاق في الإطار التالي
            def _start_slide():
                with self._lock:
                    if self._cur is not slot:
                        return
                    anim = self._anim()
                    try:
                        cur.animate_offset  = anim
                        slot.animate_offset = anim
                        cur.offset          = ft.Offset(float(-direction), 0.0)
                        slot.offset         = ft.Offset(0.0, 0.0)
                        self._push(cur, slot)
                    except Exception:
                        # في حال تعثر الأنيميشن، يتم إظهار الشاشة فوراً
                        self._finish()
                        return
                    self._start_timer(self._duration / 1000.0 + 0.05, self._finish)

            self._start_timer(0.025, _start_slide)

    # ── التبديل التفاعلي عبر السحب باللمس (Swipe) ─────────────────────

    def drag_begin(self, neighbour, side: int) -> bool:
        with self._lock:
            if self._cur is None:
                return False
            if not self._dragging:
                self._finish_locked()
            self._dragging = True
            self._side     = side
            self._other    = neighbour

            try:
                self._cur.animate_offset = _instant_anim()
                self._cur.offset = ft.Offset(0, 0)
                if neighbour is not None:
                    neighbour.animate_offset = _instant_anim()
                    neighbour.offset = ft.Offset(float(side), 0.0)
                    self.control.controls = [self._cur, neighbour]
                else:
                    self.control.controls = [self._cur]
            except Exception:
                pass
            self._push()
            return True

    def drag_move(self, fraction: float):
        with self._lock:
            if not self._dragging or self._cur is None:
                return
            try:
                self._cur.offset = ft.Offset(fraction, 0)
                if self._other is not None:
                    self._other.offset = ft.Offset(fraction + float(self._side), 0)
                self._push(self._cur, self._other)
            except Exception:
                pass

    def drag_end(self, commit: bool):
        with self._lock:
            if not self._dragging or self._cur is None:
                return
            self._dragging = False
            cur, other, side = self._cur, self._other, self._side

            anim = self._anim()
            try:
                cur.animate_offset = anim
                if other is not None:
                    other.animate_offset = anim

                if commit and other is not None:
                    cur.offset   = ft.Offset(float(-side), 0.0)
                    other.offset = ft.Offset(0.0, 0.0)
                    self._cur    = other
                    self._other  = None
                else:
                    cur.offset = ft.Offset(0.0, 0.0)
                    if other is not None:
                        other.offset = ft.Offset(float(side), 0.0)
            except Exception:
                pass

            self._push()
            self._start_timer(self._duration / 1000.0 + 0.05, self._finish)


class SwipeController:
    """متحكم السحب باللمس لتبديل التبويبات بالانزلاق"""

    def __init__(self, page: ft.Page, stack: SlideStack, neighbour, can_swipe, on_commit):
        self._page      = page
        self._stack     = stack
        self._neighbour = neighbour
        self._can_swipe = can_swipe
        self._on_commit = on_commit
        self._reset_state()

        kwargs = {}
        if not SWIPE_ALLOW_MOUSE:
            kwargs['allowed_devices'] = [
                ft.PointerDeviceType.TOUCH, ft.PointerDeviceType.STYLUS,
            ]

        self.control = ft.GestureDetector(
            content=stack.control,
            expand=True,
            drag_interval=DRAG_INTERVAL_MS,
            on_horizontal_drag_start=self._on_start,
            on_horizontal_drag_update=self._on_update,
            on_horizontal_drag_end=self._on_end,
            on_horizontal_drag_cancel=self._on_cancel,
            **kwargs,
        )

    def _reset_state(self):
        self._live   = False
        self._moving = False
        self._raw    = 0.0
        self._side   = 0
        self._nb     = None
        self._width  = 360.0

    @staticmethod
    def _eff(raw: float) -> float:
        if abs(raw) <= DEAD_ZONE_PX:
            return 0.0
        return raw - math.copysign(DEAD_ZONE_PX, raw)

    def _abort(self):
        if self._moving:
            try:
                self._stack.drag_end(False)
            except Exception:
                pass
        self._reset_state()

    async def _on_start(self, e):
        self._reset_state()
        try:
            self._live = bool(SWIPE_ENABLED and self._can_swipe())
        except Exception:
            self._live = False
        w = getattr(self._page, 'width', None)
        self._width = float(w) if w and w > 50 else 360.0

    async def _on_update(self, e):
        if not self._live:
            return
        try:
            delta = getattr(e, 'primary_delta', None)
            if delta is None:
                delta = getattr(getattr(e, 'local_delta', None), 'x', 0.0) or 0.0
            self._raw += float(delta)

            eff = self._eff(self._raw)
            if eff == 0.0:
                if self._moving:
                    self._stack.drag_move(0.0)
                return

            side = 1 if eff < 0 else -1
            if side != self._side:
                self._side = side
                self._nb   = self._neighbour(side)
                self._moving = self._stack.drag_begin(self._nb, side)
                if not self._moving:
                    self._live = False
                    return

            frac = eff / self._width
            frac = max(-1.0, min(1.0, frac))
            self._stack.drag_move(frac)
        except Exception:
            self._abort()

    async def _on_end(self, e):
        if not self._live or not self._moving:
            self._reset_state()
            return
        try:
            vx   = float(getattr(e, 'primary_velocity', 0.0) or 0.0)
            eff  = self._eff(self._raw)
            side = self._side
            commit = False

            if self._nb is not None and eff != 0.0:
                progress  = abs(eff) / self._width
                same_dir  = (vx < 0) == (eff < 0)
                fast      = abs(vx) >= FLING_VELOCITY
                fling     = fast and same_dir and abs(eff) >= FLING_MIN_PX
                reversed_ = fast and not same_dir
                commit    = (progress >= COMMIT_FRACTION or fling) and not reversed_

            self._live = self._moving = False
            if commit:
                self._on_commit(side, self._stack.drag_end)
            else:
                self._stack.drag_end(False)
        except Exception:
            try:
                self._stack.drag_end(False)
            except Exception:
                pass
        finally:
            self._reset_state()

    async def _on_cancel(self, e):
        self._abort()