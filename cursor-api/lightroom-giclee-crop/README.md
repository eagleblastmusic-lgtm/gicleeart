# Giclée — wtyczka Lightroom Classic

Kadrowanie z JSON + import folderów klientów do kolekcji.

## Wymagania

- **Adobe Lightroom Classic** (nie Lightroom chmura)
- Folder zamówienia klienta z plikami pobranymi przez GicleeApp → Poczta, np.:
  - `Oryginał zdjęcia klienta.jpg`
  - `Dane kadrowania.json`

## Instalacja

1. Skopiuj cały folder `GicleeCrop.lrplugin` do katalogu modułów Lightrooma:

   **Windows:** `%AppData%\Adobe\Lightroom\Modules\`

   Pełna ścieżka zwykle:
   `C:\Users\<Ty>\AppData\Roaming\Adobe\Lightroom\Modules\GicleeCrop.lrplugin`

2. **Zamknij Lightroom całkowicie i uruchom ponownie.**

3. Sprawdź: **Plik → Menedżer wtyczek** — na liście powinno być **Giclee Kadrowanie** (status: włączone).

4. Opcjonalnie: **Plik → Menedżer wtyczek → Dodaj** i wskaż folder `GicleeCrop.lrplugin` (jeśli nie widać po restarcie).

Możesz też uruchomić `install.bat` z tego katalogu (kopiuje wtyczkę do Modules).

## Kadrowanie z JSON

1. Zaimportuj folder zamówienia (np. `Numer zamówienia #1001`) do katalogu Lightrooma.
2. Zaznacz **`Oryginał zdjęcia klienta.jpg`** (nie podgląd mockupu).
3. **Plik → Dodatki do wtyczek → Zastosuj kadrowanie z JSON**
4. Sprawdź kadrowanie w **Wywołaj**.

## Import folderów klientów

1. **Plik → Dodatki do wtyczek → Importuj nowe foldery klientów**
2. Skrypt skanuje `E:\Firma\1. Obrazy\3. Klienci` (ścieżka w `Config.lua`).
3. W zestawie kolekcji **„Zdjęcia klientów”** tworzy kolekcje o nazwach jak foldery (np. `Numer zamówienia #1001`).
4. Do każdej kolekcji dodaje pliki **`Oryginał zdjęcia klienta.*`** — przy wielu pozycjach w zamówieniu także z sufiksem `_1`, `_2`, … (import „dodaj bez przenoszenia”).
5. Folder jest pomijany dopiero gdy **wszystkie** oryginały z dysku są już w kolekcji (stan w `data/synced_client_folders.json`).

Potem możesz zaznaczyć zdjęcie w kolekcji i uruchomić kadrowanie z JSON.

### Config.lua

```lua
CLIENT_ORDERS_DIR = "E:\\Firma\\1. Obrazy\\3. Klienci"
COLLECTION_SET_NAME = "Zdjęcia klientów"
ORIGINAL_FILE_PREFIX = "Oryginał zdjęcia klienta"
```

## Użycie (skrót — kadrowanie)

## Format JSON

Wtyczka czyta pola:

| Pole | Znaczenie |
|------|-----------|
| `sourceWidthPx`, `sourceHeightPx` | Wymiary oryginału z mockupu |
| `cropSource.x/y/width/height` | Prostokąt kadru w pikselach oryginału |

Współrzędne są przeliczane na `CropLeft/Top/Right/Bottom` (0–1) w Lightroomie. Jeśli wymiary pliku różnią się od JSON, prostokąt jest skalowany; przy dużej rozbieżności (>3%) pojawi się ostrzeżenie.

Szukane nazwy JSON w folderze zdjęcia: `Dane kadrowania.json` / `crop.json`; przy wielu pozycjach w zamówieniu także `Dane kadrowania_1.json`, `Dane kadrowania_2.json`, … (dopasowanie po sufiksie `_N` w nazwie oryginału).

## Rozwiązywanie problemów

| Problem | Co zrobić |
|---------|-----------|
| Brak menu „Dodatki do wtyczek” | Zainstaluj wtyczkę, zrestartuj LR, sprawdź Menedżer wtyczek |
| „Brak Dane kadrowania.json” | Upewnij się, że JSON leży w tym samym folderze co zdjęcie |
| „Podgląd/mockup” | Zaznacz oryginał, nie `Podgląd mockupu.jpg` |
| Kadrowanie przesunięte | Oryginał ma inne wymiary niż w JSON — sprawdź czy to ten sam plik co w sklepie |

Jeśli wtyczka nie wystarczy, plan B to skrypt Python w GicleeApp (ten sam JSON, zapis przyciętego pliku na dysk).

## Pliki w repozytorium

```
cursor-api/lightroom-giclee-crop/
  README.md
  install.bat
  GicleeCrop.lrplugin/
    Info.lua
    Config.lua
    ApplyCropFromJson.lua
    SyncClientFolders.lua
    json.lua
    data/
```

Powiązane: `assets/giclee-photo-mockup.js` (`getCropPayload`), `Komponenty/poczta/client_order_processor.py`.
