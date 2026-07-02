"""Konwersja między prostym tekstem a HTML bloków motywu Horizon."""

from __future__ import annotations

import html
import re

_HEADING_RE = re.compile(r"(?is)<(h[1-3])[^>]*>(.*?)</\1>")
_P_RE = re.compile(r"(?is)<p[^>]*>(.*?)</p>")


def parse_heading(html_text: str) -> tuple[str, str]:
    """Zwraca (tag, tekst nagłówka) — domyślnie h2."""
    raw = html_text or ""
    match = _HEADING_RE.search(raw)
    if not match:
        return "h2", ""
    tag = match.group(1).lower()
    inner = re.sub(r"(?is)<br\s*/?>", " ", match.group(2))
    inner = re.sub(r"<[^>]+>", "", inner)
    return tag, html.unescape(inner).strip()


def html_to_body_plain(html_text: str) -> str:
    """Treść bez nagłówka — akapity jako zwykły tekst (podwójna nowa linia)."""
    raw = html_text or ""
    raw = _HEADING_RE.sub("", raw, count=1)
    paragraphs: list[str] = []
    for match in _P_RE.finditer(raw):
        chunk = match.group(1)
        chunk = re.sub(r"(?is)<br\s*/?>", "\n", chunk)
        chunk = re.sub(r"<[^>]+>", "", chunk)
        chunk = html.unescape(chunk).strip()
        if chunk:
            paragraphs.append(chunk)
    if paragraphs:
        return "\n\n".join(paragraphs)
    text = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def split_combined_html(html_text: str) -> tuple[str, str, str]:
    tag, heading = parse_heading(html_text)
    body = html_to_body_plain(html_text)
    return tag, heading, body


def build_heading_html(text: str, *, tag: str = "h2") -> str:
    clean = (text or "").strip()
    if not clean:
        return ""
    safe_tag = tag if tag in {"h1", "h2", "h3"} else "h2"
    return f"<{safe_tag}>{html.escape(clean)}</{safe_tag}>"


def body_to_html(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if not parts:
        parts = [raw]
    out: list[str] = []
    for part in parts:
        lines = [ln.strip() for ln in part.split("\n") if ln.strip()]
        inner = "<br/>".join(html.escape(ln) for ln in lines)
        out.append(f"<p>{inner}</p>")
    return "".join(out)


def merge_heading_body_html(heading: str, body: str, *, tag: str = "h2") -> str:
    parts: list[str] = []
    head = build_heading_html(heading, tag=tag)
    if head:
        parts.append(head)
        parts.append("<p></p>")
    body_html = body_to_html(body)
    if body_html:
        parts.append(body_html)
    return "".join(parts)
