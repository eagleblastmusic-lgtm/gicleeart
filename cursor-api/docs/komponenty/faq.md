# Komponent: faq

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.faq.json` — pozycja menu **FAQ**.

| Plik | Rola |
|------|------|
| `Komponenty/faq/registry.py` | Mapowanie stref → ścieżki JSON; Hero FAQ deklaruje jawny selektor celu efektów grafiki |
| `Komponenty/faq/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy, eksport efektów sekcji) |
| `blocks/_accordion-row.liquid` | Wiersz FAQ — opcjonalne tła pytania/odpowiedzi z gradientem widoczności |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.faq`.

**Szablon:** `templates/page.faq.json` · **Podgląd:** `/pages/faq`

**Warianty:** domyślnie jedna wersja (`fq1`); **Dodaj nową…** kopiuje bieżącą.

## Tła obrazów w accordionie

Dla każdego pytania w strefie **Pytania i odpowiedzi** można ustawić:

- **Pytanie N — tło** → `heading_background_image`
- **Odpowiedź N — tło** → `answer_background_image` (opcjonalnie)

**Tryb jednej całości (domyślny):** gdy ustawisz tylko tło pytania, jedna warstwa grafiki pokrywa cały wiersz. Zwinięty widać górny fragment; po rozwinięciu odsłania się kontynuacja w dół — bez szwu między pytaniem a odpowiedzią.

**Tryb dwóch obrazów:** gdy podasz osobne tło odpowiedzi, pytanie i odpowiedź mają niezależne kadry.

Na froncie obraz leży pod tekstem z maską gradientu L→P (lewa strona ciemna dla czytelności, prawa odsłania grafikę).

## Efekty grafiki Hero FAQ

- `Efekty grafiki…` dotyczą pola `Tło — grafika`, nie całej sekcji ani tekstu.
- Selektor frontu pochodzi z `registry.py` i jest eksportowany jako `targetSelector` do `assets/faq-section-effects.js`.
- Runtime motywu stosuje hover i parallax wyłącznie do kontenera grafiki Hero; mobile i `prefers-reduced-motion` pozostają bez ruchu.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
