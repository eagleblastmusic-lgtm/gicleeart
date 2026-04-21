# nazwijobraz

GUI do automatycznej zmiany nazw plikow obrazow malarskich do formatu **`Autor - Tytul.ext`**.

## Jak to dziala

1. Wgrywasz / przeciagasz pliki obrazow.
2. Aplikacja czyta **autora** z dowolnego segmentu sciezki pliku (np. `.../Sisley, Alfred/...` -> `Alfred Sisley`).
   Jesli w sciezce nie ma autora, probuje go wyciagnac z **nazwy pliku** (znaki `_` traktowane jak spacje).
3. Po klikni\u0119ciu **"Wyszukaj nazwy"** dla kazdego pliku (rownolegle, kilka watkow):
   - obraz trafia tymczasowo na publiczny hosting (0x0.st, fallback catbox.moe) -- pasek **Wgrywanie**,
   - aplikacja odpyta **wszystkie ponizsze zrodla** i polaczy ich glosy -- pasek **Wyszukiwanie**:
     - **SerpAPI Google Lens** (wymaga klucza, reverse image search),
     - **Wikipedia** -- direct page lookup po nazwie pliku + OpenSearch + `prop=langlinks|pageprops`
       (zwraca tytul EN, tytul w jezyku oryginalu z 130+ langlinks oraz Wikidata Q-id w 1 requeście),
     - **Wikidata wbsearchentities + wbgetentities** (struktur. dane o obrazach + tytul EN i tytul w jezyku oryginalnym),
     - **Metropolitan Museum of Art** (collectionapi, bez klucza),
     - **Art Institute of Chicago** (api.artic, bez klucza),
     - **Wikimedia Commons** -- direct `File:<nazwa>` + ns 6/14/0 search + `extmetadata.ObjectName`
       + parsowanie szablonow `{{en|...}} {{da|...}}` z wikitext + `pageprops.wikibase_item` (most do Wikidata),
     - **SerpAPI Google text** (tylko gdy laczna pewnosc < 60%),
     - **Agregat serwisow sztuki** -- jedno zapytanie SerpAPI z filtrami `site:`
       do: invaluable.com, mutualart.com, artnet.com, sothebys.com, christies.com,
       fineartamerica.com, art.com, pixels.com, findartinfo.com,
       bruun-rasmussen.dk, picryl.com, wikiart.org, artsandculture.google.com.
   - kazde zrodlo ma wage; **najwyzsza ma nazwa pliku** (`filename` weight 10), bo czesto sam uzytkownik
     wpisal poprawny tytul. The Met/ArtIC = 6, Wikidata = 5, Lens/Wiki/Commons = 4,
     agregat aukcyjny = 3, Google text = 2.
   - kandydaci typu `File:foo.jpg` (Wikipedia/Commons file pages), `Untitled`, `DSC...`, `IMG...` sa
     odrzucane.
4. Wynik jest formatowany w **Title Case dla tytulow obrazow** (np. `Cows in Pasture, Louveciennes`,
   z malymi `of/in/the/at/by/...`, liczbami rzymskimi `II/III` i zachowaniem skrotow `MoMA`).
5. Mozesz **dwuklikiem** zedytowac tytul, lub uzyc **"Edytuj autora..."** / **"Edytuj tytul..."**.
6. **"Zmien nazwy"** nadpisuje pliki na dysku - rozszerzenia typu `.jpg.jpg` sa wykrywane
   i obcinane. Po zmianie nazwy aplikacja zapisuje **metadane** obrazu i **zawsze
   stara sie zachowac OBA tytuly: angielski + oryginalny** (np. dla obrazow duńskich,
   polskich, rosyjskich, japonskich):
   - `english_title` - priorytet: Wikidata EN, potem finalny tytul (jesli ASCII).
   - `original_title` + `original_lang` - priorytet: Wikidata original (rozne od EN),
     potem finalny tytul (jesli ma znaki diakrytyczne / cyrylice / CJK), potem hint z pliku.
   - **EXIF JPEG** (in-place przez `piexif`, bez utraty jakosci):
     `ImageDescription` + `XPTitle` = EN, `Artist` + `XPAuthor` = autor,
     `XPSubject` = tytul w jezyku oryginalnym, `XPComment` = jezyk + URL Wikidata.
   - **PNG tEXt** (`Title`, `Author`, `Description`, `OriginalTitle`, `OriginalLanguage`, `Source`).
   - **WebP EXIF** (te same pola co JPEG, przez `piexif.dump`).
   - **Sidecar** `<plik>.<ext>.metadata.json` (zawsze, dla wszystkich formatow) -
     zawiera oba tytuly i jezyk oryginalu w czytelnym JSON-ie.
7. **Wydajnosc**:
   - W obrebie jednego pliku 5 zrodel (Wiki/Wikidata/Met/ArtIC/Commons) pyta sie
     **rownolegle** zamiast sekwencyjnie.
   - Wikidata uzywa batch `wbgetentities` (1 HTTP zamiast N) i krotkiego obwodu
     przy multi-language (jesli ASCII query znalazl wystarczajaco hitow w EN,
     nie pyta innych jezykow).
   - **HTTP keep-alive** -- wszystkie zrodla dziela jedna `requests.Session`
     (modul `http_client.py`), eliminujac TLS handshake na kazde zapytanie
     (+20-30% szybciej). Plus retry z exponential backoff (3 proby) na
     500/502/503/504/429.
   - **Trwaly cache na dysku** (`.cache/nazwijobraz/<source>.json`, TTL 30 dni)
     -- przezywa restart aplikacji. Zysk: te same obrazy wyszukane drugi raz
     = 0 zapytan do API.
   - Rownolegle przetwarzanie 6 plikow naraz.
   - Lacznie ~5-10x szybciej niz wczesniej dla typowej kolejki, a powtorne
     wyszukania to milisekundy.
8. **Paski postepu** (Wgrywanie / Wyszukiwanie) sa **procentowe i animowane** -
   plynnie rosna w trakcie kazdej fazy (Lens, Wikipedia, Wikidata, Met,
   ArtIC, Commons, Google, agregat) zamiast skakac po skonczeniu pliku.
   Po kazdej fazie pojawia sie **toast z komunikatem zakonczenia**.
9. **Pewnosc jest cap-owana liczba zrodel** - 1 zrodlo (np. tylko nazwa pliku) =
   max 50%, 2 zrodla = max 80%, 3 zrodla = max 92%, 4+ zrodel = mozliwe 100%.
   W kolumnie "Status" widnieje np. `gotowe (87%, 4 zrodla)`.
10. **Cofnij ostatni rename** - osobny przycisk obok "Zmien nazwy" przywraca
    poprzednie nazwy + cofa nazwy plikow `.metadata.json`. Jeden poziom historii.
11. **Ostrzezenie low-conf** - przy renamie pozycji ponizej 40% pewnosci aplikacja
    pokazuje liste i pyta o potwierdzenie.
12. **Klik nazwy kolumny** sortuje kolejke (Status sortuje po pewnosci - rosnaco,
    zeby najmniej pewne byly na gorze).
13. **Prawy klik** na pozycji w kolejce wyswietla menu kontekstowe (Kopiuj tytul /
    Kopiuj nowa nazwe / Otworz folder pliku / Pomin / Usun).
14. **Cache per-(zrodlo, autor, query)** - dla 30 obrazow tego samego autora
    Wikidata/Met/ArtIC/Commons/Wiki sa pytane raz na unikalne zapytanie.
15. **Wikidata multi-language** - jesli nazwa pliku jest po polsku/francusku/...,
    aplikacja pyta Wikidata w tym jezyku i mapuje wynik na angielski label.

## Wymagania

- Python 3.10+
- (opcjonalnie) `pip install tkinterdnd2` dla drag-and-drop
- (opcjonalnie) `pip install piexif` zeby zapisywac EXIF in-place bez utraty jakosci JPEG
- klucz SerpAPI (free plan ma 100 zapytan/miesiac): https://serpapi.com/
  -- bez klucza dziala Wikipedia / Wikidata / The Met / Art Institute, ale brak Google Lens i Google text.

## Konfiguracja

W pliku `cursor-api/.env` dodaj:

```
SERPAPI_KEY=twoj_klucz_serpapi
```

## Uruchomienie

Z katalogu `cursor-api`:

```
python -m nazwijobraz
```

## Uwagi

- Pliki sa **tymczasowo** uploadowane na 0x0.st (publiczny hosting). Nie uzywaj dla zdjec poufnych.
- Reverse image search nie zawsze trafia w 100% poprawny tytul - zawsze zweryfikuj propozycje przed kliknieciem "Zmien nazwy".
- Na liscie pojawia sie kolumna **"Status"** z **pewnoscia** (np. "gotowe (pewnosc 75%)") - im wieksza, tym wiecej zrodel zwrocilo ten sam tytul.
