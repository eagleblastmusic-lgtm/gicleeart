# Komponent: bazapromptow

**Cel:** Własna biblioteka promptów — każdy prompt to przycisk; po kliknięciu wybór **artysty** i **obrazu** z katalogu Shopify, podmiana `[autor]` / `[tytuł]`, kopiowanie do schowka + grafika.

| Plik | Rola |
|------|------|
| `gui.py` | Okno z siatką przycisków, ładowanie katalogu |
| `select_dialog.py` | Combobox artysta → obraz, podgląd, kopiowanie |
| `catalog.py` | `load_product_catalog_rows`, placeholdery, grupowanie |
| `storage.py` | Zapis JSON w `data/prompts.json` |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Workflow

1. Przy starcie (lub **Odśwież katalog**) — produkty typu Obraz z Shopify.
2. **Klik** przycisku promptu → lista rozwijana **Artysta** → **Obraz**.
3. Podgląd promptu z podstawionymi wartościami.
4. **Kopiuj prompt** — tekst w schowku; okno pomocnicze z **Kopiuj grafikę** (Gemini: tekst i obraz osobno).
5. Placeholdery: `[autor]`, `[tytuł]`, `[tytul]`, `[Autor]`, `[title]`, `[artist]` (wielkość liter dowolna).
6. **Kontekst** — opcjonalne notatki i **grafiki referencyjne** per prompt (przycisk «Kontekst» / PPM); widoczne w podglądzie, **nie** trafiają do schowka przy «Kopiuj prompt». Grafiki można skopiować osobno («Schowek») — np. do Gemini / Nano Banana.
7. **Ctrl+klik** / PPM «Kopiuj szablon (surowy)» — sam szablon, bez wyboru produktu i bez kontekstu.
8. **Foldery** — drzewo po lewej: «Wszystkie», «Bez folderu», domyślny **Strona Główna** (+ własne foldery i **podfoldery**). **+ Podfolder** tworzy podfolder w zaznaczonym folderze. Klik prompt → **Przenieś do folderu** (toolbar lub PPM). Prompty w **Strona Główna** (i jej podfolderach): klik kopiuje szablon od razu.

## Dane

- `data/prompts.json` — szablony promptów (`text`, opcjonalnie `context`, opcjonalnie `context_images[]`, opcjonalnie `folder_id`) oraz drzewo `folders` (`parent_id` dla podfolderów)
- `data/context_images/{prompt_id}/` — pliki grafik przypisane do kontekstu promptu (jpg, png, webp, gif, bmp)
- Katalog produktów — jak w «Aktualizuj opis» / «Tytuły AI» (`load_product_catalog_rows`)

→ [`README.md`](README.md)
