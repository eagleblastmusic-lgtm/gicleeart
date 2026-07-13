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

## Workspace użytkownika

Własne zdjęcia testowe, pobrane pary Whitewall i raporty kalibracji są danymi roboczymi użytkownika, a nie cache'em.

Domyślny workspace znajduje się poza checkoutem:

```text
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\print_optimize\data\test_photos\
%LOCALAPPDATA%\GicleeArt\GicleeApp\data\Komponenty\print_optimize\data\ww_pairs\
```

Na systemach bez Windows używany jest odpowiedni użytkownikowy fallback `~/.gicleeart/GicleeApp/local/data/...`.

Zasady bezpieczeństwa:

- istniejące katalogi `Komponenty/print_optimize/data/test_photos` i `data/ww_pairs` nie są automatycznie przenoszone, scalane ani usuwane;
- jawny folder wybrany w GUI lub przekazany w CLI pozostaje dokładnie tym samym folderem;
- samo rozpoznanie domyślnej ścieżki nie tworzy katalogu;
- katalog jest tworzony dopiero przez operację wymagającą zapisu lub podczas startu GUI.

## CLI

Z katalogu `cursor-api/` (alternatywa dla GUI):

```bash
# Pojedynczy obraz (Gemini + strength 70%)
python -m Komponenty.print_optimize optimize ścieżka/zdjęcia.jpg -o out.jpg --params out.params.json

# Bez Gemini (same domyślne parametry — test pipeline)
python -m Komponenty.print_optimize optimize zdjęcie.jpg -o out.jpg --no-gemini --strength 70

# Porównanie z referencją (np. Whitewall ww70.jpg)
python -m Komponenty.print_optimize compare ww70.jpg ours70.jpg

# Domyślny bezpieczny workspace Local AppData
python -m Komponenty.print_optimize collect-pairs
python -m Komponenty.print_optimize calibrate

# Jawne foldery użytkownika pozostają autorytatywne
python -m Komponenty.print_optimize collect-pairs --input-dir D:/test_photos --output-dir D:/ww_pairs
python -m Komponenty.print_optimize calibrate D:/ww_pairs

# Gdy masz ręcznie id z DevTools (imageserver URL)
python -m Komponenty.print_optimize collect-id "0:643531663637:5fb3b1b7c81a0:1df0f0" --output-dir D:/ww_pairs
```

## GUI (GicleeApp)

Kafelek **Optymalizacja druku** w sekcji «Administracja produktu».

| Zakładka | Działanie |
|----------|-----------|
| **Optymalizuj** | Jeden plik + suwak strength + Gemini |
| **Zestaw testowy** | Upload folderu do Whitewall → pary `original` / `ww70` |
| **Kalibracja** | `ours70` + `calibration_report.json` vs Whitewall |
| **Porównaj** | dE / SSIM dwóch plików |

Pola folderów startują z bezpiecznym workspace'em Local AppData. Użytkownik może wskazać inne foldery; wybór nie jest przekierowywany ani kopiowany.

**Cała kalibracja na parach może iść przez GicleeApp** — bez ręcznego CLI.

## Struktura datasetu (`ww_pairs/`)

```text
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
| `paths.py` | bezpieczne resolvery workspace Local AppData i jawnych override'ów |

Głębszy kontekst: [`../../SHOP_KNOWLEDGE.md`](../../SHOP_KNOWLEDGE.md) — sekcja print_optimize.
