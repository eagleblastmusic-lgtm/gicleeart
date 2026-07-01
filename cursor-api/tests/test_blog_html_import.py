"""Testy importu HTML bloga."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Komponenty.blog import html_import, preview, prompts  # noqa: E402


_SAMPLE = {
    "topic": "Test temat",
    "category": "technika",
    "image_hint": "https://cdn.example.com/hero.jpg",
    "languages": {
        "pl": {
            "title": "Tytul PL",
            "summary_html": "<p>Zajawka PL</p>",
            "body_html": "<p>Tresc PL</p><h2>Naglowek</h2>",
            "tags": ["giclee", "druk"],
            "seo_title": "SEO PL",
            "seo_description": "Opis SEO PL",
        },
        "en": {
            "title": "Title EN",
            "summary_html": "<p>Summary EN</p>",
            "body_html": "<p>Body EN</p>",
            "tags": ["print"],
            "seo_title": "SEO EN",
            "seo_description": "SEO desc EN",
        },
    },
}


class TestBlogHtmlImport(unittest.TestCase):
    def test_roundtrip_preview_html(self) -> None:
        path = preview.build_preview_html(_SAMPLE)
        parsed = html_import.parse_preview_html_file(path)
        self.assertEqual(parsed["topic"], "Test temat")
        self.assertEqual(parsed["category"], "technika")
        self.assertEqual(parsed["image_hint"], "https://cdn.example.com/hero.jpg")
        pl = parsed["languages"]["pl"]
        self.assertEqual(pl["title"], "Tytul PL")
        self.assertIn("Tresc PL", pl["body_html"])
        self.assertEqual(pl["tags"], ["giclee", "druk"])
        en = parsed["languages"]["en"]
        self.assertEqual(en["title"], "Title EN")

    def test_parse_content_response_still_works(self) -> None:
        raw = """```json
{
  "topic": "x",
  "languages": {
    "pl": {"title": "A", "body_html": "<p>b</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "en": {"title": "B", "body_html": "<p>c</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "de": {"title": "C", "body_html": "<p>d</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "fr": {"title": "D", "body_html": "<p>e</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "es": {"title": "E", "body_html": "<p>f</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "nl": {"title": "F", "body_html": "<p>g</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""},
    "it": {"title": "G", "body_html": "<p>h</p>", "summary_html": "", "tags": [], "seo_title": "", "seo_description": ""}
  }
}
```"""
        data = prompts.parse_content_response(raw)
        self.assertIn("pl", data["languages"])


if __name__ == "__main__":
    unittest.main()
