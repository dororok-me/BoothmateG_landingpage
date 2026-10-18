"""CMUdict 래퍼.

단어 -> 음소열 조회. 사전에 없는 단어(OOV)는 None을 돌려주고,
호출부에서 해당 경계를 판정 대상에서 제외한다. 추측하지 않는다 —
잘못된 음소열로 만든 기대 태그는 그대로 오채점이 되기 때문이다.
"""

import re
from functools import lru_cache

import cmudict

from .phones import base

_DICT = None
_PUNCT = re.compile(r"[^a-z']+")


def _load():
    global _DICT
    if _DICT is None:
        _DICT = cmudict.dict()
    return _DICT


def normalize(word: str) -> str:
    """표기를 사전 조회용으로 정리한다."""
    w = word.lower().strip()
    w = _PUNCT.sub("", w)
    return w


@lru_cache(maxsize=8192)
def pronunciations(word: str):
    """가능한 발음 목록을 강세 제거된 음소열로 돌려준다.

    사전에 없으면 빈 튜플.
    """
    w = normalize(word)
    if not w:
        return ()
    entries = _load().get(w)
    if not entries:
        return ()
    return tuple(tuple(base(p)) for p in entries)


def primary(word: str):
    """대표 발음(사전 첫 항목). 없으면 None."""
    prons = pronunciations(word)
    return prons[0] if prons else None


def final_phone(word: str):
    """단어 마지막 음소. OOV면 None."""
    p = primary(word)
    return p[-1] if p else None


def initial_phone(word: str):
    """단어 첫 음소. OOV면 None."""
    p = primary(word)
    return p[0] if p else None


def syllable_count(word: str) -> int:
    """모음 개수로 음절을 센다. OOV면 0."""
    from .phones import VOWELS
    p = primary(word)
    if not p:
        return 0
    return sum(1 for ph in p if ph in VOWELS)
