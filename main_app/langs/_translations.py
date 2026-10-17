# -*- coding: utf-8 -*-
# main_app/langs/_translations.py

from .ar import ARABIC_DICT
from .en import ENGLISH_DICT
from .fa import PERSIAN_DICT
from .fr import FRENCH_DICT
from .de import GERMAN_DICT
from .ch import CHINESE_DICT
from .ru import RUSSIAN_DICT
from .tr import TURKISH_DICT
from .pl import POLISH_DICT
from .ur import URDU_DICT
from .es import SPANISH_DICT
from .id import INDONESIAN_DICT


class Translations:
    show_debug_ids = False

    translations = {
        'ar': ARABIC_DICT,
        'fa': PERSIAN_DICT,
        'ur': URDU_DICT,
        'en': ENGLISH_DICT,
        'fr': FRENCH_DICT,
        'de': GERMAN_DICT,
        'ch': CHINESE_DICT,
        'ru': RUSSIAN_DICT,
        'tr': TURKISH_DICT,
        'pl': POLISH_DICT,
        'es': SPANISH_DICT,
        'id': INDONESIAN_DICT,
    }

    @staticmethod
    def _dict_key(lang: str) -> str:
        return (lang or 'en').strip().lower().lstrip('_') or 'en'

    @staticmethod
    def _table(lang: str) -> dict:
        code = Translations._dict_key(lang)
        for key, table in Translations.translations.items():
            if key.lstrip('_').lower() == code:
                return table
        return {}

    @staticmethod
    def available_codes() -> list:
        return [k.lstrip('_') for k in Translations.translations]

    @staticmethod
    def get(key: str, lang: str = 'en') -> str:
        val = Translations._table(lang).get(key)
        if val is None:
            val = ENGLISH_DICT.get(key, key)

        if isinstance(val, tuple) and len(val) == 2:
            num_id, text = val

            if Translations.show_debug_ids:
                return f"[{num_id}] {text}"

            return text

        return val

    @staticmethod
    def toggle_debug_ids():
        Translations.show_debug_ids = not Translations.show_debug_ids