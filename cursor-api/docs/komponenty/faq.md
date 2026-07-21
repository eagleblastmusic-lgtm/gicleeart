# Komponent: faq

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.faq.json` — pozycja menu **FAQ**.

| Plik | Rola |
|------|------|
| `Komponenty/faq/registry.py` | Mapowanie wspólnych pól na strukturę Wersji 1 (`fq1`) i Wersji 2 (`fq2`) |
| `Komponenty/faq/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy, eksport efektów sekcji) |
| `sections/giclee-editorial-faq.liquid` | Izolowana sekcja Editorial FAQ Archive używana przez Wersję 2 |
| `assets/giclee-editorial-faq.css` | Redakcyjny indeks, asymetryczna karta i responsive layout |
| `assets/giclee-editorial-faq.js` | Progressive enhancement, morphing, hash, Theme Editor i cleanup |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.faq`.

**Szablon:** `templates/page.faq.json` · **Podgląd:** `/pages/faq`

## Warianty GicleeApp

- `fq1` — **Wersja 1**: zachowany klasyczny accordion bez zmian strukturalnych.
- `fq2` — **Wersja 2**: Editorial FAQ Archive; jest aktywną wersją i odpowiada `templates/page.faq.json`.
- `manifest.json` zachowuje oba warianty i wskazuje `fq2` jako aktywny.
- `registry.py` wybiera ścieżki pól zależnie od aktywnego wariantu, dlatego oba układy pozostają edytowalne z tego samego interfejsu.
- Efekty obrazu Hero są skopiowane do `fq2/section-effects.json`, a frontowy asset wskazuje wariant `fq2`.

## Editorial FAQ Archive — Wersja 2

- Sekcja `section_9YgpHf` używa typu `giclee-editorial-faq`.
- Każde pytanie jest bezpośrednim blokiem `faq_item` z polami `question`, `answer` i opcjonalnym `anchor`.
- Globalne `blocks/accordion.liquid`, `blocks/_accordion-row.liquid` i `snippets/accordion-custom-component.liquid` pozostają bez zmian.
- Desktop: indeks pozostaje widoczny, a aktywna odpowiedź jest przenoszona do jednej asymetrycznej karty.
- Mobile: odpowiedź rozwija się wewnątrz aktywnego wiersza; bez modala i drawera.
- No-JS: natywne `details/summary` pozostawiają wszystkie odpowiedzi dostępne.
- URL hash jest stabilizowany przez jawny `anchor` lub deterministyczny slug pytania.
- `prefers-reduced-motion` wyłącza morphing i długie animacje.
- Theme Editor wybiera właściwy blok przez `shopify:block:select`; cleanup usuwa listenery, animacje, timery i obserwatory.

## Efekty grafiki Hero FAQ

- `Efekty grafiki…` dotyczą pola `Tło — grafika`, nie całej sekcji ani tekstu.
- Selektor frontu pochodzi z `registry.py` i jest eksportowany jako `targetSelector` do `assets/faq-section-effects.js`.
- Runtime motywu stosuje hover i parallax wyłącznie do kontenera grafiki Hero; mobile i `prefers-reduced-motion` pozostają bez ruchu.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
