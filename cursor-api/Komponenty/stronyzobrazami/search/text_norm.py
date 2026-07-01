"""Normalizacja tekstu do wyszukiwania (artysta, tytul)."""

from __future__ import annotations

import re
import unicodedata


def norm_search_text(s: str) -> str:
    """Lowercase, spacje, bez znakow diakrytycznych (Durer == Durer)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.strip().lower())
