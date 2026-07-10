# Komponent: wybortrybu

**Cel:** Panel pomocniczy do przeglądania trybów pracy ChatGPT/Giclée Art (pakiet wiedzy **v37**), wybierania kombinacji i kopiowania krótkich promptów aktywacyjnych.

| Plik | Rola |
|------|------|
| `gui.py` | Okno Tkinter: zakładki Analityczne / Shopify / Kombinacje / Dodatkowe, fundament, status źródeł |
| `data_loader.py` | Wczytanie schema v2, walidacja ID/zależności, `resolve_modes_with_dependencies()` |
| `prompt_builder.py` | Krótki i pełny prompt z fundamentem, auto Shopify Snapshot, rozdzielenie Veo/Motion |
| `knowledge_sources.py` | Read-only kontrola plików `GICLEE_*_MODE_*.md` vs katalog |
| `import_from_xlsx.py` | Legacy import XLSX (parse-only domyślnie; zapis tylko z `--output-dir`) |
| `data/work_modes.json` | Schema v2: 17 formalnych trybów + workflow + legacy + fundament |
| `data/combinations.json` | Schema v2: 7 rekomendowanych kombinacji (bez zapisanych promptów) |
| `data/source/tryby_pracy_chatgpt_giclee_art.xlsx` | Źródło legacy do dev importu |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**. Kategoria Studio: **Review / GPT**.

## Schema v2

- `schema_version: 2`, `knowledge_pack: "v37"`
- **Stały fundament** (niewybieralny): `instructions_v37`, `current_app_state`, `analyst_base`
- **17 formalnych trybów:** 8 analyst + 9 Shopify
- **Workflow:** Cursor Prompt Architect
- **Legacy:** Medyczny ostrożny (poza pakietem v37)
- Komendy aktywujące: krótkie formy z COMPACT v37 (`Tryb Performance`, `Tryb Motion`, …); profile Veo: `Veo premium`, `Veo krótko`, `Veo popraw`, `TRYB FLOW`, …
- Alias `GicleeApp Architect` → fundament `analyst_base` (informacyjnie)

## Workflow

1. Otwórz **Wybór Trybu** z launchera lub Studio (Review / GPT).
2. Sprawdź status źródeł v37 (zielony / drift / niedostępny folder).
3. Przeglądaj tryby w zakładkach **Analityczne**, **Shopify** lub **Dodatkowe** (workflow + legacy).
4. Zaznacz tryby — Shopify specialist automatycznie dołącza **Shopify Snapshot** w prompcie.
5. Dla trybu Veo użyj dedykowanych przycisków profili (Veo premium / krótko / popraw / Flow / Image Prompt).
6. Zakładka **Kombinacje** — gotowe zestawy; prompty generowane live z katalogu.
7. Generator na dole — kopiuj krótki lub pełny prompt aktywacyjny.

## Kontrola plików źródłowych

Porównuje formalne `source_file` z plikami w `Pliki startowe dla GPT`:

- wzorce: `GICLEE_ANALYST_MODE_*.md`, `GICLEE_SHOPIFY_MODE_*.md`
- statusy: `current`, `drift` (missing + unknown), `unavailable`
- niedostępny folder **nie blokuje** uruchomienia (runtime = JSON w repo)

## Import XLSX (legacy)

Runtime korzysta **tylko z JSON v2** (bez openpyxl).

```bash
cd cursor-api
python -m Komponenty.wybortrybu.import_from_xlsx          # parse-only
python -m Komponenty.wybortrybu.import_from_xlsx --output-dir /ścieżka/preview
```

Domyślnie **bez zapisu** do `data/work_modes.json`.

## Testy

```bash
cd cursor-api
python -m unittest Komponenty.wybortrybu.test_wybortrybu -v
python -m compileall Komponenty/wybortrybu
```

## Relacja do Bazy Promptów

Ten komponent generuje **krótkie komendy aktywacyjne** i szkielet pełnego promptu z fundamentem v37. Pełne, rozbudowane prompty są w komponencie **Baza Promptów**.

→ [`README.md`](README.md)
