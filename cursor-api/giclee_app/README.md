# GicleeApp

Glowna aplikacja-launcher uruchamiajaca komponenty z folderu `Komponenty/`.

Po starcie pokazuje siatke kafelkow - po jednym dla kazdego komponentu wykrytego
w `cursor-api/Komponenty/`. Klikniecie kafelka odpala komponent jako osobny proces
(`python -m Komponenty.<nazwa>`).

## Uruchomienie

Z katalogu `cursor-api`:

```
python -m giclee_app
```

**Bez drugiego okna (czarna konsola):** uzyj `pythonw` zamiast `python` — okno tylko GUI:

```
pythonw -m giclee_app
```

(`pythonw.exe` lezy obok `python.exe`, np. `C:\Python314\pythonw.exe`.)
Skrot na pulpicie powinien wskazywac na **pythonw**, nie python.

### Plik .exe (PyInstaller)

Z katalogu `cursor-api` (wymaga zainstalowanego `pyinstaller`):

```
pip install pyinstaller
python -m PyInstaller giclee_app.spec --noconfirm
```

Wynik: **`dist/GicleeApp.exe`** (jeden plik, okno bez konsoli).

**Wazne:** sam launcher to osobny proces; komponenty (`Dodaj obraz`, `Nazwij obraz`, itd.)
nadal uruchamiane sa przez **systemowy Python** (`python` / `py -3` z PATH).
Na komputerze docelowym musi byc zainstalowany Python 3.11+ z zaznaczonym
„Add to PATH”, albo ustaw zmienna srodowiskowa `GICLEE_PYTHON` na pelna sciezke
do `python.exe` (np. `C:\Python314\python.exe`).

## Aktualnie dostepne komponenty

| Folder | Nazwa | Co robi |
|---|---|---|
| `dodajobraz` | Dodaj obraz | Tworzenie produktow malarskich w Shopify na podstawie zdjecia. |
| `nazwijobraz` | Nazwij obraz | Automatyczna zmiana nazw plikow obrazow na "Autor - Tytul". |
| `pobierzobraz` | Pobierz obraz | Pobieranie pelnych obrazow IIIF (np. National Gallery) przez kafelki. |
| `notatnik` | Notatnik | Osobiste notatki i instrukcje (Markdown). |

## Dodawanie nowego komponentu

1. Stworz folder `cursor-api/Komponenty/<nazwa_komponentu>/`.
2. Dodaj `__init__.py` (moze byc pusty lub z docstringiem).
3. Dodaj `__main__.py` z funkcja uruchamiajaca GUI:

   ```python
   from .gui import main

   if __name__ == "__main__":
       main()
   ```

4. (Opcjonalnie) Dodaj `component.json` z metadata kafelka:

   ```json
   {
     "name": "Wyswietlana nazwa",
     "description": "Krotki opis (1-2 linie)",
     "icon": "🎨",
     "color": "#1e88e5",
     "order": 40
   }
   ```

   - `name` -- jesli puste, uzywana jest nazwa folderu.
   - `description` -- jesli puste, brana z pierwszej linijki docstringu `__init__.py`.
   - `icon` -- emoji albo dowolny tekst. Wyswietla sie obok nazwy.
   - `color` -- akcent kafelka (lewy pasek + przycisk "Uruchom"). Hex `#rrggbb`.
   - `order` -- mniejsze = wczesniej. Komponenty bez `order` ladowane na koncu.

5. (Opcjonalnie) Dodaj `requirements.txt` z zaleznosciami specyficznymi dla komponentu.

GicleeApp **automatycznie wykrywa nowe komponenty** -- ponowne skanowanie odbywa sie
co 3 sekundy w tle (mozesz tez kliknac "Odswiez").

## Architektura

```
cursor-api/
├── giclee_app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── launcher.py             # GUI z kafelkami
│   ├── component_loader.py     # discovery komponentow
│   └── README.md
└── Komponenty/
    ├── __init__.py
    ├── dodajobraz/
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── component.json
    │   └── ...
    ├── nazwijobraz/
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── component.json
    │   └── ...
    └── pobierzobraz/
        ├── __init__.py
        ├── __main__.py
        ├── component.json
        ├── gui.py
        └── iiif_downloader.py
```

Komponenty sa **izolowane** -- kazdy uruchamia sie w osobnym procesie Pythona, wiec
crash jednego nie ubije launchera ani innych otwartych komponentow.
