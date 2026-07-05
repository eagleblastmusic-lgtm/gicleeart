# Komponent: wspolpraca

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.wspolpraca.json` — pozycja menu **Współpraca**.

| Plik | Rola |
|------|------|
| `Komponenty/wspolpraca/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/wspolpraca/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.wspolpraca`.

**Szablon:** `templates/page.wspolpraca.json` · **Podgląd:** `/pages/wspolpraca`

**Warianty:** domyślnie jedna wersja (`ws1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
