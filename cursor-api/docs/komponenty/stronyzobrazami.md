# Komponent: stronyzobrazami

**Cel:** Osobista lista linków do muzeów, galerii, katalogów i aukcji — szybki dostęp z GicleeApp + **silnik wyszukiwania** w tych kolekcjach.

| Plik | Rola |
|------|------|
| `gui.py` | Notebook: **Zakładki** + **Wyszukiwarka** + **Szukaj po obrazie** + **Pobierz obraz** |
| `search_gui.py` | UI wyszukiwania (artysta, tytuł, wyniki) |
| `image_search_gui.py` | UI wyszukiwania po obrazie (drag-and-drop, reverse image) |
| `search/image_search.py` | Silnik: SerpAPI reverse image → linki muzeów → dHash miniatur |
| `search/reverse_urls.py` | Wyciąganie linków z Google Lens / Yandex / Bing (SerpAPI) |
| `search/url_lookup.py` | URL strony muzeum → `ArtworkHit` (Met, Rijks, Artic…) |
| `search/visual_hash.py` | dHash — podobieństwo graficzne 0–100% |
| `search/engine.py` | Równoległe przeszukiwanie wielu źródeł |
| `search/adapters.py` | REST API: Met, Art Institute, Cleveland, SMK, Mia, Smithsonian, **Rijksmuseum**, **Getty**, **Belvedere**, **Newfields**, **Albertina**, **Paris Musées**, **Finnish National Gallery** |
| `search/iiif_presentation_search.py` | Wspólne wyszukiwanie IIIF Presentation (Albertina; wzór dla Belvedere) |
| `search/paris_musees_api.py` | Paris Musées — GraphQL + fallback HTML search |
| `search/fng_api.py` | Finnish National Gallery — REST search |
| `search/rijks_lod.py` | Parsowanie Linked Art JSON (nowe API Rijks) |
| `search/newfields_api.py` | Newfields — POST `/api/search` (`searchTerm`) |
| `search/download/` | Pobieranie HD: IIIF (kafelki), direct CDN, scraping strony |
| `download_gui.py` | Zakladka «Pobierz obraz» — wklej link |
| `search/errors.py` | Czytelne komunikaty bledow per zrodlo |
| `search/filters.py` | Filtr rzezby, rysunkow, **grafik/drukow**, artefaktow i publikacji (ksiazki…) |
| `search/thumbnails.py` | Cache + prefetch miniatur (mniejsze URL-e IIIF) |
| `search/artic_images.py` | Miniatury Artic — IIIF + nagłówek Referer (Cloudflare) |
| `search/mia_images.py` | Miniatury Mia — shardowany CDN (id mod 7) |
| `search/walters_images.py` | Walters — `media.csv` → miniatury i direct URL |
| `search/nga_images.py` | NGA — `published_images.csv` → IIIF thumb / service |
| `search/yale_iiif.py` | Yale — manifest IIIF (pobieranie z `tms:` ID) |
| `search/preview_urls.py` | Lazy miniatury Smithsonian (`onlineMedia` on demand) |
| `search/score.py` | Trafność wyników (artysta, tytuł, obraz, tryb) |
| `search/dedup.py` | Scalanie duplikatów między muzeami |
| `search/source_health.py` | Szybki test połączenia ze źródłami |
| `settings.py` | `data/settings.json` — katalog pobierania, wątki IIIF, limit, checkboxy |
| `batch_download.py` | Kolejka pobierania wielu zaznaczonych wyników |
| `search/artist_match.py` | Dopasowanie artysty: diakrytyki, transliteracja, fuzzy, Wikidata |
| `search/transliterate.py` | Cyrylica/greka → łacina |
| `search/wikidata_artists.py` | Aliasy artystów z Wikidata (cache JSON) |
| `search/text_norm.py` | Normalizacja tekstu wyszukiwania |
| `search/local_data.py` | CSV z GitHub: NGA, Walters (cache w `data/cache/`); indeks artystów + QID Wikidata + `cancel_check` |
| `search/smithsonian_media.py` | Smithsonian — `record_link`, miniatury i HD z `onlineMedia` (ids.si.edu) |
| `search/registry.py` | Mapowanie URL zakładki → źródło |
| `search/env_keys.py` | `SMITHSONIAN_API_KEY` — odczyt/zapis `.env` |
| `search/web_urls.py` | Fallback: link do wyszukiwania w przeglądarce |
| `storage.py` | Zapis/odczyt `data/sites.json` |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Zakładki

1. Kafelek **Strony z obrazami** → lista linków.
2. **Wklej linki…** — wiele adresów naraz (`Nazwa | https://…`).
3. Dwuklik / **Otwórz** — strona w przeglądarce.

Dane: `Komponenty/stronyzobrazami/data/sites.json`.

## Wyszukiwarka (silnik)

Zakładka **Wyszukiwarka** — na podstawie zapisanych linków rozpoznaje muzea i przeszukuje je równolegle.

| Źródło (z Twoich linków) | Integracja |
|--------------------------|------------|
| Rijksmuseum | REST `data.rijksmuseum.nl/search/collection` (Linked Art, bez klucza) |
| The Met | REST `collectionapi.metmuseum.org` |
| Art Institute of Chicago | REST `api.artic.edu` |
| Cleveland Museum of Art | REST `openaccess-api.clevelandart.org` |
| SMK (Dania) | REST `api.smk.dk` |
| Minneapolis (Mia) | REST `search.artsmia.org` (Elasticsearch) |
| National Gallery of Art | CSV GitHub + **`published_images.csv`** (miniatury IIIF w wynikach) |
| Walters Art Museum | CSV GitHub + **`media.csv`** (miniatury w wynikach) |
| Getty Museum | REST `www.getty.edu/art/collection/api/search` — bez rysunków, grafik, albumów i książek; pomija rekordy `is_parent` (zbiory) |
| Belvedere | IIIF `sammlung.belvedere.at/apis/iiif/presentation/v2/collection/search/objects` |
| Indianapolis / Newfields | POST `collections.discovernewfields.org/api/search` (tylko `Artwork`; typ/medium ze strony dzieła — filtr bez grafik); miniatury: IIIF `/full/!200,200/` (nie `__small`, bo to JSON) |
| **Albertina** | IIIF Presentation search `sammlungenonline.albertina.at/apis/iiif/presentation/v2/collection/search/objects` |
| **Paris Musées** | GraphQL `apicollections.parismusees.paris.fr/graphql` — **`PARIS_MUSEES_API_TOKEN`** ([explorer / token](https://apicollections.parismusees.paris.fr/en/explorer)); **fallback:** wyszukiwanie HTML na `parismuseescollections.paris.fr` gdy WAF blokuje GraphQL POST (typowe poza przeglądarką) |
| **Finnish National Gallery** | REST `kokoelma.kansallisgalleria.fi/api/v1/search` — **`FNG_API_KEY`**; [Swagger](https://kokoelma.kansallisgalleria.fi/api/swagger); fallback: lokalny cache `/v1/objects` |
| **Birmingham Museums Trust** | Asset Bank — scraping search + metadane `viewAsset`; **pobieranie HD** przez API Asset Bank (JPEG do ~7500×10000 px / ~100 MB bez logowania); pełny **TIF** (~7858×10489, setki MB) wymaga konta i logowania na [dams.birminghammuseums.org.uk](https://dams.birminghammuseums.org.uk) |
| Nationalmuseum (Szwecja), Mauritshuis, DMA, LACMA, Princeton, Clark, Barnes, SLAM, Städel, MK&G, Kunstmuseum Basel, NPM (Tajwan), MNK, Yale Art Gallery, Philadelphia, **DIA**, **Birmingham MA**, **RAMM**, **Public Domain Image Archive** | **Wyszukiwanie WWW** — link do katalogu w wynikach (brak publicznego API) |
| **RISD Museum** | REST `risdmuseum.org/api/v1/collection` (bez klucza; Cloudflare może blokować boty) |
| **Library of Congress** | JSON `loc.gov/search/?fo=json` (bez klucza) |
| **Wellcome Collection** | REST `api.wellcomecollection.org/catalogue/v2/works` (bez klucza) |
| **Te Papa** | REST `collections.tepapa.govt.nz/api/search` (bez klucza) |
| **Europeana** | REST `api.europeana.eu/record/v2/search.json` — **`EUROPEANA_API_KEY`** ([pro.europeana.eu](https://pro.europeana.eu/page/get-api)) |
| **NYPL Digital Collections** | REST `api.repo.nypl.org/api/v2/items/search` — **`NYPL_API_TOKEN`** ([api.repo.nypl.org](https://api.repo.nypl.org/)) |
| **Cooper Hewitt** | REST `api.collection.cooperhewitt.org/rest/` — **`COOPER_HEWITT_ACCESS_TOKEN`** ([collection.cooperhewitt.org/api](https://collection.cooperhewitt.org/api/)) |
| Smithsonian | REST `api.si.edu` — **`SMITHSONIAN_API_KEY`** w `cursor-api/.env` ([api.data.gov/signup/](https://api.data.gov/signup/)); przycisk **Klucz Smithsonian…** w zakładce Wyszukiwarka |
| Yale | Wyszukiwanie WWW (katalog blokuje boty); **pobieranie IIIF** z manifestu `manifests.collections.yale.edu/ycba/obj/{id}` |

Pola: **Artysta**, **Tytuł obrazu** (wystarczy jedno). **Limit / źródło** (1–30), **Sortuj** (trafność, źródło, artysta, tytuł). **Trafność** — scoring dopasowania tytułu/artysty; **deduplikacja** scala ten sam obraz z wielu muzeów w jeden wiersz. Wyniki **bez rzeźb, rysunków, grafik/druków (ryty, litografie, mezzotinty…), albumów/portfolio/folderów Smithsonian `[Folder]`, artefaktów i publikacji**. Dwuklik wiersza, **Otwórz link** lub klik w kolumnę **URL** → strona dzieła. Zaznaczenie → miniatura (Smithsonian: `onlineMedia` w tle, bez blokowania UI; cache odpowiedzi; prefetch top 5 w wątku). **Stop** / **Test źródeł** (ping API). **Pobierz zaznaczone** — wiele wierszy naraz. Ustawienia w `data/settings.json` (katalog, wątki, checkboxy źródeł).

**Dopasowanie artysty (…, Getty, Belvedere, Newfields, Albertina, Paris Musées, FNG):** wymagane **wszystkie** tokeny zapytania (≥3 znaki). Obsługiwane: **znaki diakrytyczne** (`Durer` = `Dürer`), **transliteracja** cyrylicy/greki (`Репин` = `Repin`), **warianty imion** (`Johann` ≈ `Johannes`), **aliasy Wikidata** (cache w `data/cache/wikidata_artist_aliases.json`, pobierane przy pierwszym wyszukiwaniu). NGA/Walters: wyniki sortowane po trafności w ramach `scan_cap` przed limitem źródła.

## Szukaj po obrazie

Zakładka **Szukaj po obrazie** — przeciągnij plik (lub kliknij pole) i szukaj w muzeach powiązanych z zakładkami.

1. **Upload** obrazu na publiczny hosting (0x0.st / catbox — jak w `nazwijobraz`).
2. **Reverse image** przez SerpAPI: Google Lens, Yandex Images, Bing Reverse Image.
3. Z wyników wybierane są **linki do stron muzeów** pasujących do Twoich źródeł; metadane pobierane z API (Met, Rijks, Artic…).
4. **dHash** — porównanie graficzne miniatur z zapytaniem; kolumna **Podob.** (0–100%).
5. Uzupełnienie tekstowe: pierwszy tytuł z Lens → wyszukiwanie słowne w tych samych źródłach.

Wymaga **`SERPAPI_KEY`** w `cursor-api/.env` (ten sam klucz co moduł `nazwijobraz`). Bez klucza — komunikat w UI. Drag-and-drop: `pip install tkinterdnd2`.

## Pobieranie obrazów (HD)

Zakładka **Pobierz obraz** — wklej link do strony dzieła, URL pliku lub IIIF. Strategie per źródło:

| Źródło | Strategia pobierania |
|--------|----------------------|
| Met, Mia (800px CDN), Cleveland (`print`), Smithsonian (ids.si.edu), **Walters (`media.csv`)** | Direct — pełny plik z CDN |
| Artic, Rijks, Belvedere, Getty, Newfields, SMK, **NGA (`published_images`)**, **Yale (manifest)** | IIIF — kafelki lub `/full/max/` |
| NGA (bez IIIF w CSV), Walters (bez obrazu), Yale (tylko strona) | Scraping strony → IIIF (`pobierzobraz` fallback) |

IIIF: retry z backoff; **checkpointy** kafelków (`.partial` + `.iiifstate.json`, wznowienie po przerwaniu); cache `info.json` i `resolve_hit` (TTL w pamięci). Ustawienia: `data/settings.json`. Checkbox **Wymuś PNG (tylko IIIF)** — aktywny gdy link/strategia to IIIF (Rijks, Artic, NGA…); **ignorowany** dla direct CDN (Met, Cleveland, Walters). Ta sama rozdzielczość, bez strat JPEG z IIIF, większy plik.

### Znane ograniczenia

- **NGA** — miniatury tylko dla obiektów w `published_images.csv`; reszta bez podglądu do scrapingu.
- **Walters** — obrazy z `media.csv` (GitHub); brak wpisu → scraping strony.
- **Smithsonian** — miniatury lazy (`onlineMedia` w wątku tła + cache; klucz API przy podglądzie/pobieraniu).
- **Yale** — katalog WWW blokuje wyszukiwanie z serwera; pobieranie działa dla linków `…/catalog/tms:ID`.
- **Rijks** — linki `…/collectie/object/Slug--hash` → trwałe ID `id.rijksmuseum.nl` → IIIF (`iiif.micr.io`).
- **Getty** — podgląd w wynikach używa IIIF 800px z manifestu wyszukiwania.

## Konfiguracja Smithsonian

W `cursor-api/.env` (lub przycisk **Klucz Smithsonian…** w zakładce Wyszukiwarka):

```env
SMITHSONIAN_API_KEY=...
```

Klucz: [api.data.gov/signup](https://api.data.gov/signup/) (darmowa rejestracja).

## Konfiguracja Paris Musées i Finnish National Gallery

W `cursor-api/.env`:

```env
PARIS_MUSEES_API_TOKEN=...
FNG_API_KEY=...
```

- Paris Musées: [apicollections.parismusees.paris.fr](https://apicollections.parismusees.paris.fr/en) (GraphQL, limit 1000 zapytań/dzień)
- Finnish National Gallery: [kansallisgalleria.fi/en/open-data](https://www.kansallisgalleria.fi/en/open-data) — dokumentacja API: [kokoelma.kansallisgalleria.fi/api/swagger](https://kokoelma.kansallisgalleria.fi/api/swagger)

Bez klucza te źródła zwracają błąd API i fallback do linku wyszukiwania WWW.

## Konfiguracja Europeana, NYPL, Cooper Hewitt

W `cursor-api/.env`:

```env
EUROPEANA_API_KEY=...
NYPL_API_TOKEN=...
COOPER_HEWITT_ACCESS_TOKEN=...
```

- Europeana: [pro.europeana.eu/page/get-api](https://pro.europeana.eu/page/get-api)
- NYPL: [api.repo.nypl.org](https://api.repo.nypl.org/) (token po rejestracji)
- Cooper Hewitt: [collection.cooperhewitt.org/api](https://collection.cooperhewitt.org/api/) (OAuth access token)

LOC, Wellcome, Te Papa i RISD nie wymagają klucza. Bez tokenu NYPL/Cooper Hewitt/Europeana — fallback WWW.

→ [`README.md`](README.md)
