# Komponent: stronablogu

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/blog.json` — pozycja menu **Strona blogu (wygląd)**.

| Plik | Rola |
|------|------|
| `Komponenty/stronablogu/registry.py` | Mapowanie stref → ścieżki JSON; Hero bloga deklaruje jawny selektor celu efektów grafiki |
| `Komponenty/stronablogu/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy, eksport efektów sekcji) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.stronablogu`.

**Szablon:** `templates/blog.json` · **Podgląd:** `/blogs/…`

**Warianty:** domyślnie jedna wersja (`sb1`); **Dodaj nową…** kopiuje bieżącą.

## Efekty Hero bloga

- `Efekty tekstu…` / `Efekty grafiki…` zapisują się per wariant w `section-effects.json`.
- Eksport frontu: `assets/blog-section-effects.js` + boot `giclee-page-section-effects-boot.js` (ładowane przy `request.page_type == 'blog'`).
- `Efekty grafiki…` dotyczą pola `Tło — grafika`; selektor pochodzi z `registry.py` (`targetSelector`).

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
