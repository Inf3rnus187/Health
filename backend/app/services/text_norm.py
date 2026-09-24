"""French text for matching: lower case, no accents, words and numbers.

« ½ », « ¼ », « ¾ » and « 1/2 » become numbers first (unicode would turn
« ½ » into « 12 »).
"""

from __future__ import annotations

import re
import unicodedata

_FRACTIONS = {"½": " 0.5 ", "¼": " 0.25 ", "¾": " 0.75 ", "⅓": " 0.33 "}
_SLASH = re.compile(r"(\d+)\s*/\s*(\d+)")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[a-z]+")
_PLURAL_FROM = 4  # « os », « riz », « pois » stay as they are
#: Words ending in s / x that are not plurals (numbers first).
_NOT_PLURAL = frozenset("deux trois six dix noix prix choix frais gras".split())


def norm(text: str) -> str:
    """Lower case, no accents, words and numbers separated by spaces."""
    return " ".join(tokens(text))


def tokens(text: str) -> list[str]:
    """The words and numbers of ``text`` (« 1,5 » kept whole)."""
    lowered = text.lower()
    for sign, number in _FRACTIONS.items():
        lowered = lowered.replace(sign, number)
    lowered = _SLASH.sub(_fraction, lowered)
    plain = unicodedata.normalize("NFKD", lowered).encode("ascii", "ignore")
    return _TOKEN.findall(plain.decode())


def singular(word: str) -> str:
    """« tomates » → « tomate », « choux » → « chou » (roughly)."""
    if (
        word not in _NOT_PLURAL
        and len(word) >= _PLURAL_FROM
        and word[-1] in "sx"
        and not word.endswith("ss")
    ):
        return word[:-1]
    return word


def _fraction(match: re.Match[str]) -> str:
    """« 1/2 » → « 0.5 »."""
    top, bottom = int(match[1]), int(match[2])
    return f" {top / bottom:g} " if bottom else " "
