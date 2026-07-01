"""Import posta blogowego z pliku HTML (format podgladu z generatora / AI).

Oczekiwany format: plik wygenerowany przez `preview.build_preview_html` lub
HTML o tej samej strukturze (zakladki + panele `#panel-{locale}`).
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from .prompts import LANGUAGES

_PANEL_RE = re.compile(
    r'<section\s+class="panel(?:\s+active)?"\s+id="panel-([a-z]{2})">(.*?)</section>',
    re.DOTALL | re.IGNORECASE,
)
_TOPIC_RE = re.compile(r"Temat:\s*<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_CATEGORY_RE = re.compile(r"Kategoria:\s*<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_IMAGE_HINT_RE = re.compile(
    r"Sugestia obrazka:\s*<em>(.*?)</em>", re.DOTALL | re.IGNORECASE,
)
_H1_RE = re.compile(r"<h1>(.*?)</h1>", re.DOTALL | re.IGNORECASE)
_DIV_INNER_RE = re.compile(
    r'<div\s+class="(summary|body)">(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_SEO_ROW_SPLIT_RE = re.compile(r'<div\s+class="seo-row">', re.IGNORECASE)
_SEO_KEY_RE = re.compile(r'<span\s+class="key">(.*?)</span>', re.DOTALL | re.IGNORECASE)
_SEO_VAL_RE = re.compile(
    r'<span\s+class="val">(.*)</span>\s*</div>',
    re.DOTALL | re.IGNORECASE,
)
_CHIP_RE = re.compile(r'<span\s+class="chip">(.*?)</span>', re.DOTALL | re.IGNORECASE)
_CHARS_SUFFIX_RE = re.compile(r'\s*<span\s+class="chars">.*?</span>\s*', re.DOTALL | re.IGNORECASE)


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _unescape(text: str) -> str:
    return html.unescape(str(text or "").strip())


def _extract_div_inner(section_html: str, class_name: str) -> str:
    for match in _DIV_INNER_RE.finditer(section_html):
        if match.group(1).lower() == class_name.lower():
            return match.group(2).strip()
    return ""


def _parse_panel(section_html: str) -> dict[str, Any]:
    h1 = _H1_RE.search(section_html)
    title = _unescape(_strip_tags(h1.group(1))) if h1 else ""

    summary_html = _extract_div_inner(section_html, "summary")
    body_html = _extract_div_inner(section_html, "body")

    seo_title = ""
    seo_description = ""
    tags: list[str] = []

    for chunk in _SEO_ROW_SPLIT_RE.split(section_html)[1:]:
        key_m = _SEO_KEY_RE.search(chunk)
        val_m = _SEO_VAL_RE.search(chunk)
        if not key_m or not val_m:
            continue
        key = _unescape(_strip_tags(key_m.group(1))).lower()
        val_html = _CHARS_SUFFIX_RE.sub("", val_m.group(1))
        if key.startswith("seo title"):
            seo_title = _unescape(_strip_tags(val_html))
        elif key.startswith("seo description"):
            seo_description = _unescape(_strip_tags(val_html))
        elif key.startswith("tagi"):
            tags = [_unescape(_strip_tags(m.group(1))) for m in _CHIP_RE.finditer(val_html)]
            tags = [t for t in tags if t]

    return {
        "title": title,
        "summary_html": summary_html,
        "body_html": body_html,
        "tags": tags,
        "seo_title": seo_title,
        "seo_description": seo_description,
    }


def parse_preview_html(content: str) -> dict[str, Any]:
    """Parsuje plik HTML podgladu. Rzuca ValueError przy bledach."""
    if not str(content or "").strip():
        raise ValueError("Plik HTML jest pusty.")

    topic = _unescape(_strip_tags((_TOPIC_RE.search(content) or [None, ""])[1]))
    category = _unescape(_strip_tags((_CATEGORY_RE.search(content) or [None, ""])[1]))
    image_hint = _unescape(_strip_tags((_IMAGE_HINT_RE.search(content) or [None, ""])[1]))

    languages: dict[str, dict[str, Any]] = {}
    for match in _PANEL_RE.finditer(content):
        code = match.group(1).lower()
        panel = _parse_panel(match.group(2))
        if panel.get("title") or panel.get("body_html"):
            languages[code] = panel

    if not languages:
        raise ValueError(
            "Nie znaleziono paneli jezykowych (#panel-pl, #panel-en, ...). "
            "Upewnij sie, ze plik pochodzi z podgladu GicleeApp (Generator tresci -> Podglad)."
        )

    pl = languages.get("pl") or {}
    if not (pl.get("title") and pl.get("body_html")):
        raise ValueError("Wersja PL jest wymagana - brak tytulu lub tresci w panelu #panel-pl.")

    known_codes = {code for code, _ in LANGUAGES}
    extra = sorted(set(languages) - known_codes)
    if extra:
        raise ValueError(f"Nieznane kody jezykow w HTML: {', '.join(extra)}")

    return {
        "topic": topic,
        "category": category,
        "image_hint": image_hint,
        "languages": languages,
    }


def parse_preview_html_file(path: str | Path) -> dict[str, Any]:
    """Wczytuje i parsuje plik HTML podgladu."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"Plik nie istnieje: {p}")
    content = p.read_text(encoding="utf-8")
    return parse_preview_html(content)
