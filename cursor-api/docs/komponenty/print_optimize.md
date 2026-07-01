# print_optimize — optymalizacja zdjęć pod druk

Komponent Python: `cursor-api/Komponenty/print_optimize/`

Cel: odpowiednik warstwy Whitewall **„AI scena → kontrast, saturacja, balans, cienie”** z suwakiem `strength` (0–100, domyślnie 70).

## Architektura

1. **Gemini Vision** (`analyze.py`) — typ sceny + parametry JSON (`CorrectionParams`)
2. **Pillow + numpy** (`apply.py`) — deterministyczna korekcja
3. **Blend** — `original * (1-s) + corrected * s`, jak `pcStrength` u Whitewall
4. **Kalibracja** — pary z Whitewall imageserver + metryki ΔE / SSIM

## Wymagania

```bash
pip install -r cursor-api/Komponenty/print_optimize/requirements.txt
playwright install chromium   # tylko collect-pairs
```

`GEMINI_API_KEY` w `cursor-api/.env` (jak inne komponenty Gemini).

## CLI

Z katalogu `cursor-api/` (alternatywa dla GUI):

```bash
# Pojedynczy obraz (Gemini + strength 70%)
python -m Komponenty.print_optimize optimize ścieżka/zdjęcia.jpg -o out.jpg --params out.params.json

# Bez Gemini (same domyślne parametry — test pipeline)
python -m Komponenty.print_optimize optimize zdjęcie.jpg -o out.jpg --no-gemini --strength 70

# Porównanie z referencją (np. Whitewall ww70.jpg)
python -m Komponenty.print_optimize compare ww70.jpg ours70.jpg

# Zbieranie par kalibracyjnych (własne zdjęcia testowe → upload Whitewall)
python -m Komponenty.print_optimize collect-pairs --input-dir ./test_photos --output-dir ./ww_pairs

# Gdy masz ręcznie id z DevTools (imageserver URL)
python -m Komponenty.print_optimize collect-id "0:643531663637:5fb3b1b7c81a0:1df0f0" --output-dir ./ww_pairs

# Batch: dla każdej pary generuj ours70 i raport calibration_report.json
python -m Komponenty.print_optimize calibrate ./ww_pairs
```

## GUI (GicleeApp)

Kafelek **Optymalizacja druku** w sekcji «Administracja produktu».

| Zakładka | Działanie |
|----------|-----------|
| **Optymalizuj** | Jeden plik + suwak strength + Gemini |
| **Zestaw testowy** | Upload folderu do Whitewall → pary `original` / `ww70` |
| **Kalibracja** | `ours70` + `calibration_report.json` vs Whitewall |
| **Porównaj** | dE / SSIM dwóch plików |

Domyślne ścieżki:

- `Komponenty/print_optimize/data/test_photos/` — wrzuć własne zdjęcia (README.txt)
- `Komponenty/print_optimize/data/ww_pairs/` — wynik zbierania i kalibracji

**Cała kalibracja na parach może iść przez GicleeApp** — bez ręcznego CLI.

## Struktura datasetu (`ww_pairs/`)

```
ww_pairs/
  portret_01/
    original.jpg    # WW preview enhancement=0 (ten sam crop/rozmiar co ww70)
    ww70.jpg
    ww100.jpg
    ours70.jpg      # po calibrate
    ours70.params.json
    manifest.json
  index.json
  calibration_report.json
```

## Metryki kalibracji

| Metryka | Interpretacja |
|---------|----------------|
| **ΔE mean** | średnia różnica koloru w LAB (niżej = bliżej Whitewall); cel orientacyjny < 8–12 na start |
| **SSIM** | podobieństwo struktury (wyżej = lepiej); > 0.85 to dobry trend |
| **PSNR** | pomocniczo |

## Uwagi

- Podgląd Whitewall (`imageserver`, `type=12`) ≠ finalny plik produkcyjny (SuperResolution, UltraHD to osobne opcje).
- `collect-pairs` używa **własnych** plików testowych; nie masowe scrapowanie cudzych motywów.
- Integracja z Workerem / mockupem klienta — następny krok (import `optimize_to_file` po uploadzie).

## Pliki

| Plik | Rola |
|------|------|
| `schemas.py` | `CorrectionParams` |
| `prompt.py` | prompt Gemini |
| `analyze.py` | wywołanie Gemini |
| `apply.py` | korekcja + blend |
| `optimize.py` | API `optimize_to_file` |
| `compare.py` | ΔE, SSIM |
| `whitewall_collect.py` | Playwright + imageserver |
| `calibrate.py` | batch kalibracji |

Głębszy kontekst: [`../../SHOP_KNOWLEDGE.md`](../../SHOP_KNOWLEDGE.md) — sekcja print_optimize.
