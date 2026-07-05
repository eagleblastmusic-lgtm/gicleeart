# Testy jednostkowe GicleeApp

## Uruchomienie

```powershell
cd cursor-api
pip install pytest
python -m pytest tests/ -v
```

## Co jest testowane

- `test_markets.py` - `compute_market_price` z roznymi walutami (PLN vs EUR) i kursami.
- `test_produkcja.py` - logika countdown utwardzania, overdue, profit summary,
  detekcja wariantow ramek, detekcja kraju (PL/zagranica).
- `test_auth.py` - hashowanie hasla pbkdf2, salt, weryfikacja, reset.
- `test_studio_categories.py` - mapa kategorii Studio vs foldery komponentów.
- `test_status_providers.py` - statusy read-only, brak crashy przy braku plików.
- `test_launcher_delegate.py` - argv subprocess, blokada inline, bez Popen.
- `test_studio_imports.py` - brak importów sync/backup/publisher/launcher.

## Konwencje

- Kazdy plik testowy importuje `sys.path.insert(0, parents[1])` zeby
  moduly `Komponenty.*` byly dostepne (nie ma zainstalowanego pakietu `giclee`).
- Testy auth uzywaja fixture `temp_auth_dir` zeby nie zapisywac w prawdziwym
  %APPDATA%/Giclee.
- Testy nie wymagaja Shopify / NBP / sieci - wszystko jest lokalnie.

## Nie jest testowane (bo wymaga UI/sieci)

- GUI Tkinter (renderowanie kafelków, dialogów, klikanie).
- Polling Shopify (wymaga sesji `.shopify_session.json` + sieci).
- Faktyczne pobieranie NBP (funkcja `get_rate` robi request HTTP).

Te rzeczy lepiej sprawdzic recznie (smoke test: uruchom GicleeApp, klik,
kliknij 'Odswiez kursy', otwórz Produkcję, zaznacz ramkę pomalowaną
z datą 3 dni temu -> sprawdź czy countdown się zeruje).
