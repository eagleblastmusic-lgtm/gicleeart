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

## Tło pod hero

Strefa **Tło pod hero** ustawia tło całej sekcji z pytaniami (`section_9YgpHf`, bezpośrednio pod hero):

- **Typ tła:** `Grafika` albo `Gradient`
- **Grafika** → przycisk **Tło…** (upload, kadrowanie, przyciemnienie) → `background_media` / `background_image` / `video`
- **Gradient** → **Wersja 1** lub **Wersja 2** (gotowe CSS w motywie); czyści media tła sekcji
- Suwaki efektu tła (niezależne):
  - **Rozmycie tła** `giclee_faq_bg_blur_px` (0–20 px)
  - **Saturacja tła** `giclee_faq_bg_saturate_pct` (0–100%)
  - **Jasność tła** `giclee_faq_bg_brightness_pct` (0–100%)
  - **Nakładka przyciemniająca** `giclee_faq_bg_dim_overlay_pct` (0–100%)
  - **Powiększenie kadru** `giclee_faq_bg_scale_pct` (0–12%)
- tryb / efekt zapisywany w `giclee_faq_bg_*` (ukryte ustawienia sekcji)

## Styl kart akordeonu

W strefie **Pytania i odpowiedzi** → **Styl kart** (`giclee_faq_accordion_style`):

| Wartość | Opis |
|---------|------|
| `style1` | Szkło + złota linia hover |
| `style2` | Uproszczony Galaxy — CSS radial na krawędzi/fill |
| `style3` | Galaxy shell/plate + świecący pierścień na krawędzi (bez orbów / Lottie / gwiazdy) |

Style 3 ładuje `faq-accordion-galaxy.css`.

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
