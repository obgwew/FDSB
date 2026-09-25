# -*- coding: utf-8 -*-
# main_app/langs/translations.py

from ._ar import ARABIC_DICT
from ._en import ENGLISH_DICT
from ._fa import PERSIAN_DICT
from ._fr import FRENCH_DICT
from ._de import GERMAN_DICT
from ._ch import CHINESE_DICT
from ._ru import RUSSIAN_DICT
from ._tr import TURKISH_DICT
from ._pl import POLISH_DICT
from ._ur import URDU_DICT


class Translations:
    show_debug_ids = False

    translations = {
        '_ar': ARABIC_DICT,
        '_fa': PERSIAN_DICT,
        '_ur': URDU_DICT,
        '_en': ENGLISH_DICT,
        '_fr': FRENCH_DICT,
        '_de': GERMAN_DICT,
        '_ch': CHINESE_DICT,
        '_ru': RUSSIAN_DICT,
        '_tr': TURKISH_DICT,
        '_pl': POLISH_DICT,
    }

    @staticmethod
    def get(key: str, lang: str = 'en') -> str:
        val = Translations.translations.get(lang, {}).get(key)
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
