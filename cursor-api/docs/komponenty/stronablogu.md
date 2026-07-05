# Komponent: stronablogu

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/blog.json` — pozycja menu **Strona blogu (wygląd)**.

| Plik | Rola |
|------|------|
| `Komponenty/stronablogu/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/stronablogu/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.stronablogu`.

**Szablon:** `templates/blog.json` · **Podgląd:** `/blogs/…`

**Warianty:** domyślnie jedna wersja (`sb1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
