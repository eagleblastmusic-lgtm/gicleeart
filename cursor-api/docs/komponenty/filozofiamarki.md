# Komponent: filozofiamarki

**Cel:** Zarządzanie faktycznie używaną animacją scrollowaną 60 FPS i jej treściami na stronie **Filozofia marki**.

| Plik | Rola |
|------|------|
| `Komponenty/filozofiamarki/registry.py` | Jakość, intro/outro, profil ruchu, ustawienia adapterów oraz alfa/tło |
| `Komponenty/filozofiamarki/gui.py` | Edytor strony oraz panel łatwej podmiany filmu |
| `Komponenty/filozofiamarki/motion_config.py` | Kanoniczne mapowanie katalogu presetów i walidacja |
| `Komponenty/filozofiamarki/video_sequence.py` | FFprobe/FFmpeg → WebP lub MP4, metadane 60 FPS/alfa, manifest i backup |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor, pełne presety, wykrywanie ustawień własnych i przywracanie rekomendacji |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.filozofiamarki`.

**Szablon:** `templates/page.filozofia-marki.json` · **Podgląd:** `/pages/filozofia-marki`

**Warianty:** `fm1` (Wersja 1), `fm2` (Wersja 2); **Dodaj nową…** kopiuje bieżącą.

## Scroll strony

Ten sam moduł jest dostępny we wszystkich wspólnych edytorach
**Sekcje strony**. Kliknij PPM i wybierz **Dodaj „Scroll strony”…**. Edytor
dodaje jedną ukrytą sekcję konfiguracyjną do bieżącego szablonu i pokazuje ją
na liście jako zwykłą strefę **Scroll strony**. Ponowne użycie polecenia otwiera
istniejącą strefę zamiast tworzyć drugi, konkurencyjny kontroler.

Strefa **Scroll strony** ma cztery warianty:

- **Standardowy** — natywne przewijanie przeglądarki, bez przechwytywania kółka.
- **Płynny — lekki** — własny, krótki smoothing bez biblioteki zewnętrznej.
- **Lenis** — lokalna kopia Lenis 1.3.25; nie korzysta z CDN.
- **Własny** — pełna kontrola parametrów technicznych istniejącego silnika.

Pole **Płynność / responsywność** działa w trybie Płynny. Zakres to 0–100%,
a wartość wyższa skraca doganianie kółka. Przy 75% tryb Płynny używa około
74 ms stałej czasowej i maksymalnie 800 px wyprzedzenia.

Po wybraniu Lenis pojawia się osobny, domyślnie zwinięty akordeon
**Ustawienia Lenis**. Zawiera profile:

- **Zbalansowany** — `lerp=0.245`, mnożnik kółka `1.05`;
- **Responsywny** — `lerp=0.32`, mnożnik `1.00`;
- **Filmowy** — `lerp=0.14`, mnożnik `0.90`;
- **Własne ustawienia** — zapisuje `lerp`, mnożnik kółka, `smoothWheel`,
  `overscroll`, obsługę kotwic i zatrzymanie bezwładności przy nawigacji.

Wartości własne są częścią szablonu bieżącego wariantu, więc przechodzą przez
zwykłe **Zapisz**, historię wersji, kopię zapasową i wdrożenie motywu.

Wewnątrz akordeonu znajduje się również biblioteka **Moje warianty Lenis**.
Pozwala utworzyć dowolną liczbę nazwanych konfiguracji, zastosować wybraną,
nadpisać ją bieżącymi wartościami, zmienić nazwę albo usunąć. Biblioteka jest
zapisywana lokalnie w
`Komponenty/filozofiamarki/data/lenis-scroll-variants.json`. Zastosowanie
wariantu kopiuje wszystkie jego parametry do bieżącej wersji strony i ustawia
profil **Własne ustawienia**, dlatego wdrożony frontend nie odczytuje pliku
biblioteki i pozostaje od niego niezależny.

Lenis jest ładowany przed `assets/giclee-page-smooth-scroll.js`, ma
`autoRaf`, `smoothWheel`, `anchors` i natywne przewijanie dla pól formularzy,
modali oraz zagnieżdżonych kontenerów. Na urządzeniach dotykowych i przy
`prefers-reduced-motion` runtime wraca do scrolla natywnego. Diagnostyczny
parametr `?giclee_page_scroll_mode=lenis` pozwala przetestować Lenis bez
zapisywania wariantu; `smooth`, `custom` i `standard` działają analogicznie.

## Podmiana wideo

1. Kliknij **Wybierz i przygotuj wideo…** albo upuść film na panel.
2. Wskaż plik MP4, WebM, MOV lub MKV.
3. Wybierz `Film MP4`, `Gotowy WebM — bez konwersji` albo `Klatki WebP`
   oraz `720p` albo `1080p`.
4. Komponent przygotowuje tylko wybrany wariant i aktualizuje jego manifest.
   Gotowy WebM jest kopiowany 1:1; MP4 i WebP są generowane przez FFmpeg.
   Dla filmu powstaje również lokalny, nazwany pakiet biblioteczny, więc kolejny
   import nie usuwa możliwości powrotu do poprzedniego materiału.
5. Poprzedni wariant trafia do rotacyjnej kopii ZIP (zachowywane są trzy ostatnie).
6. Użyj wdrożenia w edytorze, aby wysłać manifest, renderer i zasoby.

Film może mieć przezroczystość. WebM z VP9 jest dekodowany przez `libvpx-vp9`, aby zachować kanał alfa.

Aktywny wariant wybierasz polami **Sposób odtwarzania**, **Format filmu** i
**Jakość wyświetlania**. Gdy sposobem jest **Film**, pole **Konkretny plik**
pokazuje tylko materiały zgodne z rodziną sekcji, formatem i jakością.
**Domyślny slot** zachowuje stare działanie. Po zapisaniu wyboru GicleeApp
kopiuje wskazany pakiet biblioteczny do stabilnej nazwy runtime, dzięki czemu
`theme dev` i selektywny deploy nie muszą przesyłać wszystkich dużych wersji.
Klatki 720p i 1080p są zapisywane jako WebP RGBA;
1080p używa jakości 95, aby nie zmieniać kolorów jak JPEG. Filmy 720p i 1080p
mają klatkę kluczową na każdej klatce, dzięki czemu `<video>` może być
synchronizowane ze scrollem również podczas cofania.

Gotowy WebM musi mieć dokładnie 1280×720 albo 1920×1080, zależnie od wybranego
slotu. Panel pokazuje jego kodek, alfę i odstęp klatek kluczowych. Najpłynniejszy
scrub zapewnia WebM z GOP=1; dłuższy GOP pozostaje obsługiwany, ale może
zwiększyć koszt seekowania.

## Charakter odtwarzania

W głównej animacji pola te znajdują się wewnątrz strefy
**Animacja przewijana** jako domyślnie zwinięty akordeon
**Charakter odtwarzania**. Nie zajmują osobnej pozycji na liście sekcji.

Profil ruchu jest wspólny dla wybranego źródła 720p/1080p. Panel udostępnia:
preset, tempo, easing/Bézier, smoothing, lag, bezwładność, damping, limit
nadrabiania, zachowanie zatrzymania, kierunek, zakres materiału, interpolację,
końcowe płynne domknięcie hamowania, dead zone MP4/WebP, rounding, preload i
cache. Ręczna zmiana przełącza preset na **Własne ustawienia**, a
**Przywróć zalecane ustawienia** ustawia **Delikatny luksusowy**. Płynne
domknięcie odmierza oryginalne klatki według FPS źródła; nie miesza pikseli i
nie dodaje smug do kanału alfa.

Runtime ma jeden wspólny scheduler `requestAnimationFrame`. MP4 i WebM
utrzymują wyłącznie najnowszy seek, a WebP używa kolejki target-first i
ograniczonego LRU.
Szczegóły, diagnostyka oraz dokładne wartości presetów są w dokumentacji
kanonicznej.

## Tło pierwszego video scrolla

W sekcji **Animacja przewijana** przycisk **Dodaj tło…** ustawia tło za filmem:

- obraz → `assets/giclee-philosophy-scroll-bg.webp` + tryb `asset`
- WebM z alfą → `assets/giclee-philosophy-scroll-bg.webm` + tryb `webm`

**Usuń tło** wraca do trybu Auto.

Przełącznik **Paralaksa tła (mysz, desktop)** zapisuje
`scroll_background_parallax` w ustawieniach pierwszego Film-scrolla. Gdy
włączony, warstwa tła (obraz lub WebM) subtelnnie reaguje na kursor
(±22×±14 px, overscan 1.08); film scrolla i napisy intro zostają na miejscu.
Wyłączone na mobile oraz przy `prefers-reduced-motion`. Runtime czyta
`data-background-parallax` z `snippets/media.liquid` i montuje warstwę w
`assets/giclee-scroll-scrub-video.js`.

## Ekran cytatu

Sekcja listy **Ekran cytatu** dotyczy sticky ekranu z cytatem (przed portalem
Wrota). Przycisk **Dodaj tło…** podmienia:

- `assets/giclee-fm-quote-bg.webp`

PNG/JPG są konwertowane do WebP; WebP jest kopiowany 1:1. **Usuń tło** kasuje
plik z `assets`. Runtime (`giclee-filozofia-quote-pin.js`) ładuje obraz tylko
gdy plik istnieje na CDN — wtedy sticky cytatu dostaje klasę `has-fm-quote-bg`
i `background-size: cover`.

Suwaki nieprzezroczystości (0–100%) sterują czarnymi pasami nad obrazem tła:

- **Tło tekstu** — sekcja cytatu,
- **Górny separator — nad kreską** / **pod kreską**,
- **Dolny separator — nad kreską** / **pod kreską**.

Przełącznik **Paralaksa tła (mysz, desktop)** (`fm_quote_bg_parallax_enabled`) pozwala włączyć lub wyłączyć ruch tła cytatu pod kursorem myszy.

Wartości zapisują się w ustawieniach `section_tAj94h` wariantu.

## Tło paralaksy po Wrotach

Sekcja listy **Tło paralaksy — po Wrotach** podmienia stałe assety motywu:

- `assets/giclee-fm-parallax-bottom.webp` — obraz Bottom

Przycisk **Dodaj tło Bottom…** przyjmuje WebP, PNG albo JPG. Tło startuje
na końcówce filmu Wrota (crossfade w `giclee-filozofia-quote-pin.js`) i
pozostaje jedyną warstwą paralaksy. Moduł nie renderuje warstwy Middle ani
dawnej sekcji **Treść 3D**.

Przełącznik **Paralaksa tła (mysz, desktop)** zapisuje
`fm_bg_parallax_enabled` w ustawieniach bloku Wrota. Gdy włączony (domyślnie),
warstwa Bottom reaguje na kursor (±52×±32 px). Wyłączenie zostawia statyczne
tło Bottom oraz teksty cinematic-quote i galerię Przed i po — bez ruchu pod
kursorem. Runtime czyta flagę z `#giclee-fm-wrota-parallax-config` emitowanego
w `snippets/media.liquid`.

Na tle Bottom działa animacja `cinematic-quote`. Tło robi crossfade z końcową
fazą filmu Wrota, a sam tekst zaczyna wchodzić dopiero po zakończeniu filmu.
Pierwszy napis ma trzy równe fazy:

1. wejście tekstu — 0.6 viewportu,
2. przypięcie kompletnego napisu — 0.6 viewportu,
3. animacja chowania — 0.6 viewportu.

Po jego pełnym schowaniu pojawia się drugi napis: „W tym procesie traktuję je
jak materię kulturową…”. Wchodzi przez centralną maskę z impulsem świetlnym,
falą słów z blur/3D oraz subtelnymi akcentami kluczowych pojęć. Drugi napis
również ma fazy wejście, nieruchomy pin i wyjście po 0.6 viewportu każda.
Łączny runway tekstów wynosi 3.6 viewportu.

Podczas fazy pin każdy z dwóch napisów uruchamia własny kinowy „oddech” GSAP:
`scale: 1.025`, przesunięcie `y: -3`, `duration: 3.2`, `yoyo: true`,
`repeat: -1`. Pętla startuje od początku dopiero po ukończeniu wejścia,
zatrzymuje się i resetuje przed wyjściem oraz jest wyłączona dla
`prefers-reduced-motion`.

Postęp osi czasu jest wyliczany bezpośrednio z przewijania, dlatego wszystkie
fazy działają również w odwrotnym kierunku bez ponownego odtwarzania od początku.

## Galeria „Przed i po”

Po wyjściu drugiego napisu zaczyna się sekcja listy **Przed i po**. Panel
GicleeApp pozwala ustawić od 0 do 12 slajdów oraz wgrać dla każdego osobny plik
**Przed** i **Po**. PNG i JPG są konwertowane do WebP; WebP jest kopiowany bez
zmiany. Sloty mają stabilne nazwy:

- `assets/giclee-fm-before-after-01-before.webp`
- `assets/giclee-fm-before-after-01-after.webp`
- analogicznie do numeru `12`.

Liczba slajdów (`before_after_count`) jest zapisana w szablonie bieżącego
wariantu. W tym samym miejscu zapisują się `before_after_motion_blur`,
`before_after_film_grain`, `before_after_bg_transparent`,
`before_after_bg_radial_opacity`, `before_after_bg_linear_opacity`,
`before_after_preserve_prev_bg` oraz
wersjonowany JSON `before_after_texts_json`.
Panel udostępnia edycję wszystkich widocznych napisów wspólnych (nazwa
archiwum, podpowiedź scrolla, etykiety Przed/Po, podpowiedź suwaka i etykieta
numeru karty), a także tytułu, podpisu i typu każdej karty. Zasoby galerii,
`giclee-fm-before-after.js/css`, `media.liquid`, schemat bloku i skrypty
strony są częścią kontrolowanego wdrożenia komponentu.

Frontend odwzorowuje układ `preview.html`: talię kart 3D, licznik, kropki,
nawigację, ambient light, siatkę i filmowy szum. Każda aktywna karta ma pionowy
suwak porównania obsługiwany myszką, dotykiem oraz klawiaturą. Obraz „Przed”
zachowuje oryginalne kolory (`filter: none`). Przełącznik **Efekt smużenia**
usuwa blur kart bocznych i przejść, nie zmieniając kolorystyki obrazów.
Przełącznik **Animowane filmowe ziarno** wyłącza warstwę proceduralnego szumu
SVG na całym ekranie galerii. Przełącznik **Przezroczystość tła** pozwala
sterować dwoma warstwami tła (radialny blob i liniowy gradient) suwakami
0–100%; wyłączony przywraca klasyczne pełne tło.
Przełącznik **Zachowaj winietę i efekty tła z poprzedniego ekranu** zostawia
pod kartami winietę Bottom oraz inne efekty tła z fazy napisów cinematic-quote
(paralaksa Bottom nadal reaguje na kursor). Wyłączenie chowa całą warstwę
poprzedniego ekranu na czas galerii.

Przy wgrywaniu obrazu GicleeApp zachowuje plik źródłowy i automatycznie tworzy
wariant `*-display.webp` przeznaczony do strony. Wariant WWW ma maksymalnie
2200 px szerokości i 7 megapikseli, dzięki czemu karta zachowuje ostrość także
na ekranie Retina, ale nie rozpakowuje wielotysięcznych oryginałów do pamięci
przeglądarki. Runtime ładuje obrazy asynchronicznie i ma awaryjny fallback do
oryginału.

Karty są powiązane bezpośrednio z postępem scrolla strony. Każda karta otrzymuje
odcinek `0,8 vh` fizycznego runwayu, dlatego przewijanie w dół przechodzi do
następnych obrazów, a cofanie scrolla odtwarza talię symetrycznie wstecz.
Galeria nie przechwytuje kółka i nie zatrzymuje Lenis. W fazie kart utrzymuje
pełną nieprzezroczystość, a po ostatniej karcie robi crossfade do samej
paralaksy Bottom, która pozostaje przez końcową fazę hold.

Podczas aktywnej galerii niewidoczne warstwy filmu Wrota i napisów nie są
malowane (winieta/efekty tła mogą zostać, gdy włączono zachowanie poprzedniego
tła), scrub nie jest ponownie budzony dla niezmienionej klatki, a odległe
karty są usuwane z kompozycji. Paralaksa Bottom nadal reaguje na kursor pod
kartami. Ziarno animuje mały kafel zamiast warstwy 300% viewportu.

Górna czarna krawędź gradientu grafiki cytatu jest sprzężona z menu.
Kontener cytatu zachowuje oryginalne `top: 0`; runtime nie przesuwa grafiki,
tekstu ani separatorów. Po rozpoczęciu pinu przesuwa wyłącznie górną warstwę
gradientu, aż jej czarny początek zetknie się z dołem menu. Od tej chwili
gradient zaczyna się dokładnie pod menu, podąża za jego chowaniem i wraca
symetrycznie przy scrollowaniu w górę.

→ [`README.md`](README.md) · jedyny kanoniczny kontrakt modułu i instrukcja
dla AI: [`Film-scroll.md`](../../../docs/Film-scroll.md)
