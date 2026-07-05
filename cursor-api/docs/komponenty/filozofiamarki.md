# Komponent: filozofiamarki

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.filozofia-marki.json` — pozycja menu **Filozofia marki**.

| Plik | Rola |
|------|------|
| `Komponenty/filozofiamarki/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/filozofiamarki/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.filozofiamarki`.

**Szablon:** `templates/page.filozofia-marki.json` · **Podgląd:** `/pages/filozofia-marki`

**Warianty:** domyślnie jedna wersja (`fm1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
