"""Small text helpers shared by resume extraction and rendering."""

from __future__ import annotations

import re


_CLAUSE_BOUNDARY = re.compile(r",|;|:|\s+(?:e|and|para|for|to)\s+", re.IGNORECASE)
_TRAILING_CONNECTOR = re.compile(r"\s+(?:e|and|para|for|to)$", re.IGNORECASE)
_TERMINAL_ELLIPSIS = re.compile(r"(?:\.{3,}|\u2026+)\s*$")


def truncate_at_clause_boundary(text: object, max_chars: int) -> str:
    """Shorten text without ellipses, preferring a clause boundary before max_chars."""
    clean = remove_terminal_abbreviation_ellipsis(re.sub(r"\s+", " ", str(text or "")).strip())
    if not clean or max_chars <= 0:
        return ""
    if len(clean) <= max_chars:
        return clean

    prefix = clean[:max_chars]
    boundaries = [match.start() for match in _CLAUSE_BOUNDARY.finditer(prefix)]
    useful_boundaries = [pos for pos in boundaries if pos >= max_chars * 0.5]
    if useful_boundaries:
        shortened = prefix[:useful_boundaries[-1]]
    elif " " in prefix:
        shortened = prefix.rsplit(" ", 1)[0]
    else:
        shortened = prefix

    shortened = shortened.rstrip(" ,;:-")
    return _TRAILING_CONNECTOR.sub("", shortened).rstrip(" ,;:-")


def remove_terminal_abbreviation_ellipsis(text: object) -> str:
    """Remove a generated trailing ellipsis and any dangling connector before it."""
    clean = str(text or "").strip()
    without_ellipsis = _TERMINAL_ELLIPSIS.sub("", clean)
    if without_ellipsis == clean:
        return clean
    without_ellipsis = without_ellipsis.rstrip(" ,;:-")
    return _TRAILING_CONNECTOR.sub("", without_ellipsis).rstrip(" ,;:-")
