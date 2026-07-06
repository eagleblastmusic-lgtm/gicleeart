# Komponent: gicleeframe

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.giclee-frame.json` — pozycja menu **Giclée Frame**.

| Plik | Rola |
|------|------|
| `Komponenty/gicleeframe/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/gicleeframe/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.gicleeframe`.

**Szablon:** `templates/page.giclee-frame.json` · **Podgląd:** `/pages/giclee-frame`

**Strefy:** 8 sekcji editorial (media-with-content) + 9 separatorów + legacy main-page — kolejność jak na stronie live.

**Studio planning (F1):** [`giclee_app/docs/gicleeframe-planning.md`](../../giclee_app/docs/gicleeframe-planning.md) — panel planistyczny w GicleeApp Studio (dry-run, readiness, bez writera). W Studio karta `gicleeframe` **nie** otwiera tego legacy edytora.

**Warianty:** domyślnie jedna wersja (`gf1`); **Dodaj nową…** kopiuje bieżącą.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
