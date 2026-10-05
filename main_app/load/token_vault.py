# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/token_vault.py
#
# تخزين توكنات البوتات في مخزن النظام الآمن بدل ملف config.json:
#   Windows -> Credential Manager   | macOS/iOS -> Keychain
#   Android -> Keystore             | Linux     -> libsecret
#
# لا يوجد هنا مفتاح تشفير مكتوب في الكود ولا خوارزمية مخصصة:
# التشفير ومفتاحه يديرهما نظام التشغيل نفسه.

import asyncio
import json
import os

import flet as ft
import flet_secure_storage as fss

_KEY_PREFIX = "fdsb.bot_token."
_TIMEOUT = 5  # ثوانٍ؛ بدل مهلة Flet الافتراضية (10 ثوانٍ) لكل استدعاء


class TokenVault:
    _storage: "fss.SecureStorage | None" = None
    # نسخة في ذاكرة العملية فقط (وليس على القرص) لتُقرأ من كود متزامن/threads بدون await
    _cache: dict[str, str] = {}

    # ── التهيئة ────────────────────────────────────────────────────────────
    @classmethod
    def attach(cls, page: ft.Page) -> None:
        """يجب استدعاؤها مرة واحدة عند بدء التطبيق."""
        if cls._storage is not None:
            return
        cls._storage = fss.SecureStorage()
        page.services.append(cls._storage)
        page.update()

    @classmethod
    def _require(cls) -> "fss.SecureStorage":
        if cls._storage is None:
            raise RuntimeError("TokenVault.attach(page) must be called first.")
        return cls._storage

    # ── هوية البوت = اسم مجلده داخل app_data ───────────────────────────────
    @staticmethod
    def bot_id_from_dir(bot_dir: str) -> str:
        return os.path.basename(os.path.normpath(bot_dir))

    @staticmethod
    def _key(bot_id: str) -> str:
        return f"{_KEY_PREFIX}{bot_id}"

    # ── العمليات الأساسية ──────────────────────────────────────────────────
    @classmethod
    async def set(cls, bot_id: str, token: str) -> None:
        if not token:
            raise ValueError("Empty token.")
        await asyncio.wait_for(cls._require().set(cls._key(bot_id), token), _TIMEOUT)
        cls._cache[bot_id] = token

    @classmethod
    async def get(cls, bot_id: str) -> str:
        value = await asyncio.wait_for(cls._require().get(cls._key(bot_id)), _TIMEOUT)
        if value:
            cls._cache[bot_id] = value
        return value or ""

    @classmethod
    async def get_for_dir(cls, bot_dir: str) -> str:
        """الطريقة المفضلة لباقي الملفات: token = await TokenVault.get_for_dir(bot_dir)"""
        return await cls.get(cls.bot_id_from_dir(bot_dir))

    @classmethod
    async def remove(cls, bot_id: str) -> None:
        """استدعها عند حذف البوت."""
        cls._cache.pop(bot_id, None)
        await asyncio.wait_for(cls._require().remove(cls._key(bot_id)), _TIMEOUT)

    # ── قراءة متزامنة من الذاكرة (تُستخدم في واجهة المستخدم) ────────────────
    @classmethod
    def get_cached(cls, bot_id: str) -> str:
        return cls._cache.get(bot_id, "")

    @classmethod
    def get_cached_for_dir(cls, bot_dir: str) -> str:
        if not bot_dir:
            return ""
        return cls.get_cached(cls.bot_id_from_dir(bot_dir))

    @classmethod
    def forget_cached(cls, bot_id: str) -> None:
        cls._cache.pop(bot_id, None)

    @classmethod
    async def preload(cls, app_data_dir: str) -> int:
        """يقرأ توكنات كل البوتات من المخزن الآمن إلى الذاكرة مرة واحدة عند بدء التطبيق."""
        loaded = 0
        if not os.path.isdir(app_data_dir):
            return loaded
        for entry in os.scandir(app_data_dir):
            if not entry.is_dir():
                continue
            if not os.path.isfile(os.path.join(entry.path, "bot_files", "config.json")):
                continue
            try:
                if await cls.get(entry.name):
                    loaded += 1
            except Exception as e:
                print(f"[TokenVault] preload failed for {entry.name}: {e}")
                if isinstance(e, TimeoutError) or "Timeout" in str(e):
                    break
        return loaded

    @classmethod
    async def has(cls, bot_id: str) -> bool:
        return await asyncio.wait_for(cls._require().contains_key(cls._key(bot_id)), _TIMEOUT)

    # ── ترحيل التوكنات القديمة (النص العادي داخل config.json) ───────────────
    @classmethod
    async def migrate_plaintext(cls, app_data_dir: str) -> tuple[int, list[str]]:
        """
        ينقل أي توكن مخزن كنص عادي إلى المخزن الآمن، ثم يحذفه من config.json.
        لا يحذف النص العادي إلا بعد التأكد أن القراءة من المخزن الآمن تعيد نفس القيمة.
        يرجع (عدد ما تم ترحيله, أسماء البوتات التي فشل ترحيلها).
        """
        migrated = 0
        failed: list[str] = []

        if not os.path.isdir(app_data_dir):
            return migrated, failed

        for entry in os.scandir(app_data_dir):
            if not entry.is_dir():
                continue

            config_path = os.path.join(entry.path, "bot_files", "config.json")
            if not os.path.isfile(config_path):
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                token = (config.get("token") or "").strip()
                if not token:
                    continue

                bot_id = entry.name
                await cls.set(bot_id, token)

                if await cls.get(bot_id) != token:
                    raise RuntimeError("read-back verification failed")

                config.pop("token", None)
                config["token_storage"] = "secure"

                tmp_path = config_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, config_path)

                migrated += 1
            except Exception as e:
                print(f"[TokenVault] migration failed for {entry.name}: {e}")
                failed.append(entry.name)
                # انتهاء المهلة = المخزن الآمن غير متاح أصلاً (الإضافة غير مبنية في العميل)،
                # فلا فائدة من تجربة بقية البوتات وانتظار المهلة لكل واحد منها
                if isinstance(e, TimeoutError) or "Timeout" in str(e):
                    break

        return migrated, failed