# FAQ i troubleshoot

## "Pobierz obraz" - HTTP 400 dla kazdego kafla
Pewnie nieobslugiwana kombinacja `quality.format`. Aplikacja ma juz
auto-fallback (`native`->`default`, `tif`->`jpg`), ale jezeli z jakichs
powodow dalej leci 400, sprawdz w logu:
```
[info] Serwer nie wspiera quality='X'. Uzywam 'Y'
```

## "Nazwij obraz" - upload trwa wiecznie
Sprawdz log - czas uploadu jest tam loggowany:
```
[upload] plik.jpg -> https://0x0.st/abc.jpg (1.42 MB, 0.87s)
```
Jezeli >5s przy malych plikach -> problem z routingiem lub VPN.
Aplikacja race'uje 0x0.st i catbox.moe - bierze szybszego.

## "Dodaj obraz" - brak Krok 2 wkleja
Sprawdz czy schowek nie jest pusty. Aplikacja nie wkleja jezeli pole jest puste.

## GicleeApp - kafelki migaja
To bylo. Naprawione (`pack_propagate(False)` zamiast `grid_propagate(False)`).
Jezeli wraca - zglos i sprawdze.

## "Notatnik" - moja notatka zniknela
- Sprawdz folder `Komponenty/notatnik/notatki/` w Eksploratorze.
- Pliki to zwykle `.md` - mozesz przywrocic z kosza/git history.

## Komponent nie pojawia sie w GicleeApp
1. Sprawdz czy folder ma plik `__main__.py`.
2. Sprawdz w terminalu: `python -m Komponenty.<nazwa>` - czy startuje?
3. GicleeApp rescanuje co 3s - poczekaj chwile.
4. Klik **Odswiez** w toolbarze.
