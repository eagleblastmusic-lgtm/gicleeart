# Komponent: kontakt

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.contact.json` — pozycja menu **Kontakt**.

| Plik | Rola |
|------|------|
| `Komponenty/kontakt/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/kontakt/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.kontakt`.

**Szablon:** `templates/page.contact.json` · **Podgląd:** `/pages/contact`

**Warianty:** domyślnie jedna wersja (`ko1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
