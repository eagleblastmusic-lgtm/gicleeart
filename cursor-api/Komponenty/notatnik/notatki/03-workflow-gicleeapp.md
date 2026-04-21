# Workflow z GicleeApp

Codzienne uzycie 4 komponentow w typowej kolejnosci.

## 1. Pobierz obraz (jezeli to nowy obraz z muzeum)
- Wkleic URL strony National Gallery / IIIF (lub liste z `.txt`).
- **Folder docelowy**: `H:/Nowe obrazy/` (lub gdzie tam trzymasz).
- Quality `oryginalna`, Format `oryginalny` - aplikacja sama negocjuje z serwerem.
- Pliki ladowanie do podfolderow autora: `da Vinci, Leonardo/`, `van Gogh, Vincent/`.

## 2. Nazwij obraz (jezeli pobrales obrazy z innych zrodel)
- Przeciagnij pliki/foldery na okno.
- **Wyszukaj nazwy** - aplikacja pyta 8 zrodel rownolegle (Lens, Wiki, Wikidata, Commons, Met, ArtIC...).
- Sprawdz wyniki w kolumnie "Tytul" + procent pewnosci.
- **Zmien nazwy** - przemianuje pliki + zapisze metadane (EXIF + sidecar JSON).
- W razie czego: **Cofnij ostatni rename** jednym przyciskiem.

## 3. Dodaj obraz (publikacja w Shopify)
- Przeciagnij gotowe pliki (`Artysta - Tytul.jpg`).
- **Krok 1: Wygeneruj prompt (Opus)** - tekst kopiowany do schowka.
- Wklej do Cursora/ChatGPT (Opus 4.x najlepiej radzi sobie z duzymi listami).
- Wklej odpowiedz JSON w **Krok 2** - klik w pole automatycznie wkleja schowek.
- Aplikacja parsuje, dodaje produkty, dogrywa zdjecia.

## 4. Notatnik
- Dla nowych powtarzajacych sie zadan -> **Nowy temat** -> zapisz instrukcje
  zeby nie szukac potem przez godziny.

## Skroty na pulpit
- `python -m giclee_app` z folderu `cursor-api/` -> launcher z kafelkami.
- Mozesz utworzyc `.bat`/`.lnk` na pulpicie:
  ```
  cd /d H:\Projekty CURSOR\Nowe\pusty\cursor-api
  python -m giclee_app
  ```
