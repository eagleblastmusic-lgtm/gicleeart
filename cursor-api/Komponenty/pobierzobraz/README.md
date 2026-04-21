# pobierzobraz

GUI do pobierania obrazow w pelnej rozdzielczosci z serwerow IIIF (np. National Gallery, Rijksmuseum, J. Paul Getty Museum, Library of Congress).

## Jak to dziala

1. Wpisz **URL strony obrazu** (np. `https://www.nationalgallery.org.uk/paintings/...`) -- aplikacja sama wykryje IIIF service id na stronie.
2. ALBO wpisz **URL info.json** wprost (jesli go znasz).
3. Wybierz nazwe pliku wynikowego (.png) -- puste = automatyczna z URL-a.
4. Ustaw `Workers`, `Timeout`, `Quality` i `Format` (jpg jest najszybszy).
5. Klik **Pobierz obraz** -- pasek postepu pokazuje % pobranych kafelkow.

Pobieranie wznawia sie z miejsca przerwania (state plik `<nazwa>.state.json`).

## Wymagania

- Python 3.10+
- `pip install -r requirements.txt` (requests, Pillow, numpy)

## Uruchomienie samodzielne

Z katalogu `cursor-api`:

```
python -m Komponenty.pobierzobraz
```

Albo CLI bez GUI:

```
python -m Komponenty.pobierzobraz.iiif_downloader --page-url "https://..."
```

## Licencja

Skrypt `iiif_downloader.py` pochodzi z projektu `iiif_full_download` autora.
