"""pobierzobraz - GUI do pobierania pelnych obrazow z serwerow IIIF (np. National Gallery).

Wykorzystuje skrypt `iiif_downloader.py` do pobierania kafelkow IIIF i sklejania ich
w jeden plik PNG. GUI dodaje:
- pole na URL strony obrazu (auto wykrywanie IIIF) lub URL info.json,
- pasek postepu z procentami,
- live log z postepem pobierania,
- konfigurowalny output, workers, quality, format.
"""
