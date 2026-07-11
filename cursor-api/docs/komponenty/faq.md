# Komponent: faq

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.faq.json` — pozycja menu **FAQ**.

| Plik | Rola |
|------|------|
| `Komponenty/faq/registry.py` | Mapowanie stref → ścieżki JSON; Hero FAQ deklaruje jawny selektor celu efektów grafiki |
| `Komponenty/faq/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy, eksport efektów sekcji) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.faq`.

**Szablon:** `templates/page.faq.json` · **Podgląd:** `/pages/faq`

**Warianty:** domyślnie jedna wersja (`fq1`); **Dodaj nową…** kopiuje bieżącą.

## Efekty grafiki Hero FAQ

- `Efekty grafiki…` dotyczą pola `Tło — grafika`, nie całej sekcji ani tekstu.
- Selektor frontu pochodzi z `registry.py` i jest eksportowany jako `targetSelector` do `assets/faq-section-effects.js`.
- Runtime motywu stosuje hover i parallax wyłącznie do kontenera grafiki Hero; mobile i `prefers-reduced-motion` pozostają bez ruchu.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
