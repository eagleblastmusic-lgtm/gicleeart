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

## Tło paralaksy po Wrotach

Sekcja listy **Tło paralaksy — po Wrotach** podmienia stałe assety motywu:

- `assets/giclee-fm-parallax-bottom.webp` — obraz Bottom
- `assets/giclee-fm-parallax-middle.webp` — obraz Middle
- `assets/giclee-fm-parallax-middle.webm` — opcjonalny Middle jako WebM z alfą
- `assets/giclee-fm-parallax-config.json` — `middleKind`: `image` | `webm`

Przycisk **Dodaj tło Middle…** przyjmuje obraz albo WebM z kanałem alfa
(pętla + `mix-blend-mode: screen`). Warstwy startują na końcówce filmu Wrota
(crossfade w `giclee-filozofia-quote-pin.js`).

Po crossfade Middle wjeżdża od dołu (0.6vh), potem sekcja **Treść 3D**:
dwie pary tekst (lewa) + kontener przed/po (prawa), każda z fade in →
hold 0.6vh → fade out, na końcu Middle zjeżdża w dół (0.6vh).

→ [`README.md`](README.md) · jedyny kanoniczny kontrakt modułu i instrukcja
dla AI: [`Film-scroll.md`](../../../docs/Film-scroll.md)
