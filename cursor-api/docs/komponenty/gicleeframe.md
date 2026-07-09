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

**Studio planning (F1 + F2):** [`giclee_app/docs/gicleeframe-planning.md`](../../giclee_app/docs/gicleeframe-planning.md) — panel planistyczny w GicleeApp Studio: inventory strony (F2), dry-run, RAM draft, readiness, bez writera. W Studio karta `gicleeframe` **nie** otwiera tego legacy edytora.

**Warianty:** domyślnie jedna wersja (`gf1`); **Dodaj nową…** kopiuje bieżącą.

**Efekty per sekcja (tekst + grafika):** W panelu **Edycja sekcji** przy strefach editorial (np. Archiwalne passe-partout) — przyciski **Efekty tekstu…** (scroll reveal + hover nagłówka/treści) i **Efekty grafiki…** (parallax + hover zdjęcia). Zapis per wariant: `Komponenty/gicleeframe/data/variants/<id>/section-effects.json`. Eksport do motywu: `assets/giclee-frame-section-effects.js` + boot `giclee-page-section-effects-boot.js` (ładowane na `template.suffix == 'giclee-frame'`). Asset regeneruje się przy zapisie efektów, **Zapisz** i **Wdróż motyw…**.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
