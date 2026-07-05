# Komponent: katalog

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/collection.json` — pozycja menu **Katalog**.

| Plik | Rola |
|------|------|
| `Komponenty/katalog/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/katalog/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.katalog`.

**Szablon:** `templates/collection.json` · **Podgląd:** `/collections/…`

**Warianty:** domyślnie jedna wersja (`ka1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
