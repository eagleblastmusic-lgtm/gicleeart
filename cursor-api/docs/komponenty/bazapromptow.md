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
6. **Kontekst** — opcjonalne notatki per prompt (przycisk «Kontekst» / PPM); widoczne w podglądzie, **nie** trafiają do schowka przy «Kopiuj prompt».
7. **Ctrl+klik** / PPM «Kopiuj szablon (surowy)» — sam szablon, bez wyboru produktu i bez kontekstu.

## Dane

- `data/prompts.json` — szablony promptów (`text`, opcjonalnie `context`)
- Katalog produktów — jak w «Aktualizuj opis» / «Tytuły AI» (`load_product_catalog_rows`)

→ [`README.md`](README.md)
