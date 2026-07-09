# Komponent: bazapromptow

**Cel:** Własna biblioteka promptów — każdy prompt to przycisk; po kliknięciu wybór **artysty** i **obrazu** z katalogu Shopify, podmiana `[autor]` / `[tytuł]`, kopiowanie do schowka + grafika.

| Plik | Rola |
|------|------|
| `gui.py` | Okno z siatką przycisków, ładowanie katalogu |
| `select_dialog.py` | Combobox artysta → obraz, podgląd, kopiowanie |
| `catalog.py` | `load_product_catalog_rows`, placeholdery, grupowanie |
| `storage.py` | Zapis JSON w `data/prompts.json` |
| `media_preview.py` | Odtwarzanie fragmentu wideo w podglądzie (OpenCV lub ffmpeg) |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Workflow

1. Przy starcie (lub **Odśwież katalog**) — produkty typu Obraz z Shopify.
2. **Klik** przycisku promptu → lista rozwijana **Artysta** → **Obraz**.
3. Podgląd promptu z podstawionymi wartościami.
4. **Kopiuj prompt** — tekst w schowku; okno pomocnicze z **Kopiuj grafikę** (Gemini: tekst i obraz osobno).
5. Placeholdery: `[autor]`, `[tytuł]`, `[tytul]`, `[Autor]`, `[title]`, `[artist]` (wielkość liter dowolna).
6. **Kontekst** — notatki, **grafiki**, **filmiki**, **pliki**. Podgląd po najechaniu: **Grafika** lub **Filmik**; dla filmu zakres **od–do (s)** i płynne odtwarzanie **boomerang** (zapętlone do przodu i wstecz w wybranym fragmencie, tempo z FPS źródła).
7. **Ctrl+klik** / PPM «Kopiuj szablon (surowy)» — sam szablon, bez wyboru produktu i bez kontekstu.
8. **Foldery** — drzewo po lewej: «Wszystkie», «Bez folderu», domyślny **Strona Główna** (+ własne foldery i **podfoldery**). **+ Podfolder** tworzy podfolder w zaznaczonym folderze. Klik prompt → **Przenieś do folderu** (toolbar lub PPM). Prompty w **Strona Główna** (i jej podfolderach): klik kopiuje szablon od razu.

## Dane

- `data/prompts.json` — m.in. `context_hover_preview`, `context_video_preview_start_sec`, `context_video_preview_end_sec` (zakres boomerang w sekundach, z dokładnością do 0,01 s, np. `3.5`; `end=0` → domyślnie +3 s od startu)
- `data/context_images/{prompt_id}/` — grafiki (jpg, png, webp, gif, bmp)
- `data/context_videos/{prompt_id}/` — filmiki (mp4, webm, mov, avi, mkv, m4v, wmv; max 200 MB) + plik `{id}_poster.jpg`
- `data/context_files/{prompt_id}/` — inne pliki (pdf, txt, md, zip…; bez wykonywalnych)
- Katalog produktów — jak w «Aktualizuj opis» / «Tytuły AI» (`load_product_catalog_rows`)

→ [`README.md`](README.md)
