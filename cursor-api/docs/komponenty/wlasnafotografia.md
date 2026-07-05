# Komponent: wlasnafotografia

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/product.szablon-wlasna-fotografia.json` — pozycja menu **Własna fotografia**.

| Plik | Rola |
|------|------|
| `Komponenty/wlasnafotografia/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/wlasnafotografia/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.wlasnafotografia`.

**Szablon:** `templates/product.szablon-wlasna-fotografia.json` · **Podgląd:** `PDP produktu`

**Warianty:** domyślnie jedna wersja (`wf1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
