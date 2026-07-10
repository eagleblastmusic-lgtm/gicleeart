# Komponent: notatnik

**Cel:** Osobiste notatki Markdown (Shopify CLI, workflow, FAQ).

Folder danych: `Komponenty/notatnik/notatki/`.

Tryb: `subprocess`.

## Grafiki w notatkach

W trybie edycji można wkleić grafikę bezpośrednio ze schowka:

- standardowym `Ctrl+V`, gdy schowek zawiera obraz,
- przyciskiem `Wklej grafikę` na pasku Markdown,
- przez skopiowanie obrazu lub obsługiwanego pliku graficznego w Eksploratorze Windows.

Grafika jest zapisywana jako PNG w ukrytym katalogu:

`Komponenty/notatnik/notatki/.assets/`

Do treści notatki trafia zwykłe, względne odwołanie Markdown `![Wklejona grafika](...)`. Podgląd Notatnika wyświetla lokalne grafiki bezpośrednio pomiędzy akapitami. Ścieżki są automatycznie przeliczane po przeniesieniu notatki do innego rozdziału. Zdalne adresy i ścieżki wychodzące poza katalog Notatnika nie są wczytywane jako obrazy.

Funkcja korzysta z biblioteki Pillow. W razie jej braku:

`python -m pip install Pillow`

## Obsługa dwuklikiem

- dwuklik na rozdziale rozwija lub zwija jego zawartość,
- dwuklik na notatce otwiera dialog zmiany nazwy,
- ta sama zmiana nazwy działa również dla kopii notatki widocznej w sekcji `⭐ Ulubione`,
- dwuklik nie zmienia treści notatki i nie uruchamia trybu edycji.

## Ręczna kolejność notatek

Notatki w każdym rozdziale można przesuwać niezależnie:

- przyciskami `↑ Wyżej` i `↓ Niżej` pod drzewkiem,
- poleceniami `Przenieś wyżej` / `Przenieś niżej` w menu kontekstowym,
- skrótami `Alt+Up` i `Alt+Down`, gdy fokus znajduje się na drzewku.

Kolejność jest zapisywana lokalnie w:

`Komponenty/notatnik/notatki/.note_order.json`

Metadane nie zmieniają nazw, ścieżek ani treści plików `.md`. Rozdziały nadal są sortowane alfabetycznie przed notatkami. Nowe notatki trafiają na koniec swojego rozdziału. Brakujący lub uszkodzony plik kolejności powoduje bezpieczny powrót do układu alfabetycznego.

Sekcja `⭐ Ulubione` pozostaje wirtualna i alfabetyczna — jej pozycje nie są przesuwane.

→ [`README.md`](README.md) · [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md)
