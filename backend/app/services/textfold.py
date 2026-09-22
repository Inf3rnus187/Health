"""Accent- and case-insensitive text matching (French medical names)."""

from __future__ import annotations

import unicodedata


def fold(text: str) -> str:
    """Lowercase, accent-free, single-spaced text for containment tests."""
    plain = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return " ".join(plain.lower().split())


def same_name(left: str, right: str) -> bool:
    """Whether two names designate the same thing (one contains the other)."""
    a, b = fold(left), fold(right)
    return bool(a and b) and (a in b or b in a)
