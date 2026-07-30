# Dodaj tekst — instrukcja modułu dla AI

## Znaczenie polecenia

Polecenie `wstaw moduł Dodaj tekst` oznacza podłączenie istniejącego,
wspólnego modułu warstw tekstowych GicleeApp. Nie twórz drugiego edytora,
lokalnego odpowiednika ani osobnej pustej sekcji Shopify.

Warstwa tekstowa jest przypisana do stabilnego `sectionKey` rzeczywistej
sekcji Shopify. Jedna sekcja może zawierać wiele warstw. Zmiana nazwy sekcji
nie zmienia klucza, identyfikatora warstwy ani przypisania danych.

## Gdzie moduł działa

- wspólne edytory z panelem `Sekcje strony`;
- edytor `Sekcje strony głównej`;
- specjalny widok strony GICLÉE FRAME™ wraz z inventory.

Pod listą sekcji znajduje się przycisk `Dodaj tekst…`. Po wybraniu sekcji jej
panel pokazuje listę warstw i akcje: dodaj, edytuj, zmień nazwę, przesuń,
usuń. Dwuklik otwiera edycję. Dla wiersza będącego wyłącznie ustawieniem
globalnym przycisk ma pozostać nieaktywny z czytelnym wyjaśnieniem.

## Model i zapis

Każdy wariant przechowuje plik `text-layers.json` obok własnej kopii
szablonu:

```text
schemaVersion
sections.<sectionKey>[]
  id, name, enabled, order
  content
  layout
  motion
  pin
  importedStyle
```

Brak pliku oznacza pustą listę. Nie usuwaj nieznanych kluczy sekcji:
zachowaj je jako osierocone dane i pokaż ostrzeżenie. Identyfikatory warstw
muszą pozostać stabilne po zmianie nazwy i kolejności. Kopia wariantu kopiuje
cały katalog wariantu, więc również `text-layers.json`.

Kod modelu i zapisu:

- `cursor-api/Komponenty/_shared/theme_page_editor/text_layers.py`
- `cursor-api/Komponenty/_shared/theme_page_editor/text_layers_export.py`

## Edytor

Użyj wspólnego okna z
`cursor-api/Komponenty/_shared/theme_page_editor/text_layers_dialog.py`.
Edytor obejmuje:

- treść: H1, H2, H3, akapit, podtytuł, eyebrow, cytat i podpis;
- normalny układ lub pozycję absolutną, kotwicę 3×3, X/Y, szerokość,
  wyrównanie, z-index i padding;
- desktop jako bazę oraz opcjonalne nadpisania tablet/mobile; brak
  nadpisania oznacza dziedziczenie najbliższej wartości;
- presety wejścia i wyjścia z parametrami ograniczonymi przez model;
- pin 0–1000 vh, pozycję od góry, początek/koniec oraz tryby mobile:
  dziedzicz, włącz, wyłącz, własne;
- globalną bibliotekę własnych presetów dostępną we wszystkich komponentach.

## Wstaw kod

Importer znajduje się w
`cursor-api/Komponenty/_shared/theme_page_editor/text_code_importer.py`.
Wklejony kod jest tylko materiałem do adaptacji:

- JavaScript nigdy nie jest zapisywany ani wykonywany;
- usuwane są skrypty, event handlery, iframe, formularze oraz aktywne obiekty,
  niebezpieczne URL-e oraz `@import`;
- bezpieczny HTML działa jako pełny komponent zajmujący układ współrzędnych
  wybranej sekcji, a nie jako akapit w wąskiej kolumnie;
- zachowywane są elementy konstrukcyjne i dekoracyjne, listy, tabele,
  `picture`, obrazy, audio/wideo oraz statyczny SVG;
- zachowywane są pseudo-elementy, responsywne `@media`, bezpieczne
  `@supports`/`@container`, animacje `@keyframes`, pozycjonowanie absolutne
  i własne zmienne CSS;
- CSS jest ograniczony selektorem
  `[data-giclee-text-layer-id="<stabilne-id>"]`;
- identyfikatory HTML/SVG, odwołania do nich i nazwy animacji są
  automatycznie poprzedzane stabilnym ID warstwy, aby komponenty się nie
  zderzały;
- dozwolone są wyłącznie użyte fonty HTTPS z Google Fonts;
- zachowanie `IntersectionObserver` lub `.is-visible` jest tłumaczone na
  bezpieczne zachowanie runtime (`threshold`, `rootMargin`, jednorazowe lub
  odwracalne wejście), bez nakładania drugiej animacji GicleeApp;
- użytkownik przed zastosowaniem widzi raport zmian.

Wierność wizualna HTML/CSS jest celem importu. Nie kopiuj jednak surowego
`<script>` ani globalnego CSS do motywu. Dowolna logika JavaScript, formularze,
iframe, canvas i osadzane obiekty wykonywalne pozostają niedozwolone. Jeżeli
komponent wymaga interakcji innej niż rozpoznane wejście przy przewijaniu,
trzeba dodać ją jawnie do bezpiecznego runtime modułu.

## Frontend i wdrożenie

Wspólne pliki runtime:

- `assets/giclee-text-layers.js`
- `assets/giclee-text-layers.css`
- konfiguracja `assets/giclee-text-layers-<slug-szablonu>.js`
- loader w `snippets/scripts.liquid`

Konfigurację generuj z aktywnego `text-layers.json` podczas kontrolowanego
zastosowania wariantu. Dodaj runtime, loader i konfigurację strony do jawnej
listy wdrożeniowej. Zwykły zapis wariantu nie może samodzielnie wdrażać zmian
do Shopify.

Runtime ma:

- tworzyć warstwy wewnątrz wskazanej sekcji;
- reagować w obie strony przewijania i anulować poprzednią animację po
  szybkiej zmianie stanu;
- przebudować układ po zmianie breakpointu lub reduced motion;
- reagować na `shopify:section:load`;
- używać jednego sticky runway wewnątrz sekcji; wysokość sekcji wyznacza
  najdłuższe przypięcie, bez generowania pustych sekcji.

## Walidacja przed zakończeniem

Sprawdź co najmniej:

1. zapis/odczyt, stabilne ID, kolejność, dziedziczenie i kopiowanie wariantu;
2. usuwanie skryptów, eventów, niedozwolonych URL-i i globalnego CSS;
3. dodanie wielu warstw, zmianę nazwy, kolejności, usuwanie i dwuklik;
4. flow, absolute 3×3, desktop/tablet/mobile, animację w górę i w dół;
5. pin 0/100/200/1000 vh oraz mobile inherit/on/off/custom;
6. podgląd, kontrolowane zastosowanie wariantu i listę wdrożeniową;
7. brak regresji Film-scroll, Scroll strony i zmiany nazw sekcji.
