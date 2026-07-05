#!/usr/bin/env python3
"""Generator dokumentacji komponentów stron menu."""

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs" / "komponenty"

TEMPLATE = """# Komponent: {id}

**Cel:** Edycja wyglądu i treści szablonu motywu `{template}` — pozycja menu **{menu}**.

| Plik | Rola |
|------|------|
| `Komponenty/{id}/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/{id}/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.{id}`.

**Szablon:** `{template}` · **Podgląd:** `{preview}`

**Warianty:** domyślnie jedna wersja (`{prefix}1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
"""

ITEMS = [
    ("gicleeframe", "Giclée Frame", "templates/page.giclee-frame.json", "/pages/giclee-frame", "gf"),
    ("wlasnafotografia", "Własna fotografia", "templates/product.szablon-wlasna-fotografia.json", "PDP produktu", "wf"),
    ("katalog", "Katalog", "templates/collection.json", "/collections/…", "ka"),
    ("wspolpraca", "Współpraca", "templates/page.wspolpraca.json", "/pages/wspolpraca", "ws"),
    ("filozofiamarki", "Filozofia marki", "templates/page.filozofia-marki.json", "/pages/filozofia-marki", "fm"),
    ("kontakt", "Kontakt", "templates/page.contact.json", "/pages/contact", "ko"),
    ("stronablogu", "Strona blogu (wygląd)", "templates/blog.json", "/blogs/…", "sb"),
    ("faq", "FAQ", "templates/page.faq.json", "/pages/faq", "fq"),
    ("losujobraz", "Losuj Obraz", "templates/page.losuj-produkt.json", "/pages/losuj-produkt", "lo"),
]

if __name__ == "__main__":
    for cid, menu, template, preview, prefix in ITEMS:
        (DOCS / f"{cid}.md").write_text(
            TEMPLATE.format(id=cid, menu=menu, template=template, preview=preview, prefix=prefix),
            encoding="utf-8",
        )
        print(cid)
