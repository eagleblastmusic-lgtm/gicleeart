# Komponent: losujobraz

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.losuj-produkt.json` — pozycja menu **Losuj Obraz**.

| Plik | Rola |
|------|------|
| `Komponenty/losujobraz/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/losujobraz/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.losujobraz`.

**Szablon:** `templates/page.losuj-produkt.json` · **Podgląd:** `/pages/losuj-produkt`

**Warianty:** domyślnie jedna wersja (`lo1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
