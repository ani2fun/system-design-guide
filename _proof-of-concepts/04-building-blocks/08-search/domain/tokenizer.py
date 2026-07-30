"""Analyzer — turn text into index terms. Lowercase, split on non-alphanumerics,
drop a small stop-word list. Real engines add stemming, synonyms, and language
handling; the principle (text → normalized terms) is the same.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or that the to with".split()
)


def analyze(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOPWORDS]
