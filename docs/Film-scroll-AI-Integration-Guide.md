# KANONICZNA INSTRUKCJA DLA AI — DODAWANIE ANIMOWANYCH ELEMENTÓW

> Ten dokument jest kanoniczną instrukcją dla modeli AI rozszerzających system animacji GicleeApp. Przed dodaniem nowego elementu animowanego AI musi przeanalizować ten dokument oraz istniejącą implementację. Nie wolno tworzyć równoległego systemu animacji, osobnej pętli renderującej ani nowego sposobu zarządzania postępem, jeżeli istniejący mechanizm można rozszerzyć.

Przed zmianą przeczytaj także [`Film-scroll.md`](Film-scroll.md). Kod i te dwa
dokumenty są źródłem prawdy; nie projektuj systemu na podstawie dawnych rozmów.

## Cel i obsługiwane kategorie

Instrukcja obejmuje:

- **A. DOM:** tekst, karta, przycisk, obraz, dekoracja, tło; zwykle
  `transform` i `opacity`;
- **B. MP4:** scrollowany H.264 przez najnowszy `video.currentTime`;
- **C. sekwencja klatek:** WebP przez canvas, preload i bounded cache;
- **D. element z alfą:** WebP/PNG/canvas lub sprawdzony format wideo z alfą;
- **E. element zsynchronizowany:** tekst, światło, hotspot, podpis lub warstwa
  używająca tego samego `renderedProgress`.

## Mapa systemu i zasady modyfikacji

| Plik | Co robi / kiedy zmieniać | Kiedy nie zmieniać | Ważne elementy |
|---|---|---|---|
| `assets/giclee-scroll-scrub-video.js` | Scheduler, model ruchu, adaptery i API. Zmieniaj dla nowego zachowania runtime. | Nie dodawaj równoległego skryptu ani listenera. | `CentralScheduler`, `MotionState`, `BaseController`, `ScrollNativeVideo`, `ScrollFrameCanvas`, `DeclarativeDomAnimation`, `registerElement` |
| `assets/giclee-scroll-motion-presets.json` | Jedyny katalog wartości presetów. | Nie kopiuj wartości do GUI. | `recommended`, `presets` |
| `snippets/media.liquid` | DOM, `data-*`, wybór adaptera, źródła i manifestu. | Nie renderuj MP4 i canvasu jednocześnie. | `.media-block--scroll-scrub`, `[data-scroll-native-video]`, `[data-scroll-frame-canvas]` |
| `blocks/_media-without-appearance.liquid` | Schema Shopify. Zmień, gdy ustawienie ma być zapisane. | Nie trzymaj edytowalnego ustawienia tylko w JS. | pola `scroll_motion_*`, alfa i tło |
| `cursor-api/Komponenty/filozofiamarki/registry.py` | Pola i UX GicleeApp. | Nie duplikuj walidacji katalogu. | `FILOSOPHIA_ZONES` |
| `cursor-api/Komponenty/filozofiamarki/motion_config.py` | Łączenie katalogu z panelem i walidacja. | Nie wpisuj tu drugiej kopii presetów. | `FIELD_TO_SETTING`, `validate_motion_settings` |
| `cursor-api/Komponenty/_shared/theme_page_editor/types.py`, `gui_shell.py` | Ogólny mechanizm presetów i kontrolek. | Nie zmieniaj dla lokalnej cechy, jeśli wystarcza registry. | `TemplateZone`, obsługa presetów |
| `cursor-api/Komponenty/filozofiamarki/video_sequence.py` | FFprobe/FFmpeg, manifesty, alfa, FPS, backup. | Nie dekoduj ciężkich zasobów w runtime, jeśli powinny być przygotowane wcześniej. | `prepare_sequence`, `prepare_native_video`, `VideoMetadata` |
| `templates/page.filozofia-marki.json`, `variants/*.json` | Dane instancji i wariantów. | Nie traktuj jako globalnego katalogu presetów. | ustawienia bloku |
| `docs/Film-scroll.md` i ten plik | Kontrakt i instrukcja kanoniczna. | Nie zostawiaj ich nieaktualnych po zmianie architektury. | model, API, checklisty |

Breakpointy nie mają osobnego profilu ruchu. Responsive CSS i automatyczny
budżet cache działają w obecnej instancji. Jeżeli breakpointowe ustawienia staną
się konieczne, rozszerz istniejący model i zachowaj fallback do wartości
desktopowych.

## Zasada jednego silnika

- Wszystkie elementy używają istniejącego postępu i `CentralScheduler`.
- Nie twórz listenera `scroll` dla każdego elementu.
- Nie twórz osobnej bezwarunkowej pętli `requestAnimationFrame`.
- W zdarzeniu scroll nie wykonuj seeku, fetchu, dekodowania ani zapisów DOM.
- Renderuj tylko zmienioną wartość i zatrzymuj pracę poza aktywną sekcją.
- Element synchroniczny z obrazem używa `renderedProgress`; `globalProgress`
  (`rawProgress`) stosuj tylko do celowo natychmiastowej reakcji.

Wyjątek wymagający własnego cyklu musi być technicznie uzasadniony, najpierw
sprawdzony pod kątem podłączenia do schedulera, jawnie uruchamiany/zatrzymywany,
kompletnie czyszczony i opisany w obu dokumentach.

## Procedura

### 1. Analiza i klasyfikacja

Przeczytaj oba dokumenty i runtime. Sprawdź podobny element. Ustal:

- typ A–E, źródło, format, wymiary, FPS i liczbę klatek;
- alfę na podstawie metadanych/pikseli, nie rozszerzenia;
- zakres postępu, preset, mobile, reduced motion i fallback;
- czy element potrzebuje `rawProgress`, `targetProgress` czy
  `renderedProgress`.

### 2. Dane

Ustawienia edytowalne dodaj do istniejącej schema Shopify i `registry.py`.
Przekaż je przez `snippets/media.liquid` jako `data-*`, odczytaj i zwaliduj w
istniejącym runtime. Dodaj bezpieczny fallback dla starszych danych.

Profil ruchu jest wspólny dla jakości. Metadane źródła są techniczne i należą do
manifestu: `fps`, `frameCount`, `width`, `height`, `codec`, `pixelFormat`,
`hasAlpha`, `alphaMode`, `sourceFps`, `sourceFrameCount`, `sourceHasAlpha`,
`fullSourceFrameUse`.

### 3. Mapowanie postępu

Runtime wykonuje kolejno: clamp → tempo → easing → kierunek → zakres materiału
→ lag → interpolacja/smoothing/inertia → limit nadrabiania → końcowy tail
pacing → zabezpieczenie przed przestrzeleniem. Element dodatkowy mapuje gotowy
postęp na swój lokalny odcinek:

```js
const localProgress = window.GicleeScrollFrameCanvas.mapProgress(
  context.renderedProgress,
  0.20,
  0.65
);
const eased = window.GicleeScrollFrameCanvas.applyEasing(
  localProgress,
  'ease-out'
);
```

Nie nakładaj tego samego easingu drugi raz, jeśli nie jest to świadoma animacja
lokalna.

#### Płynne domknięcie hamowania

`scroll_motion_tail_pacing` uruchamia się dopiero po zatrzymaniu wejścia, gdy
odległość do celu mieści się w `scroll_motion_tail_window_frames`. Runtime
korzysta z `sourceFps` adaptera i odmierza sąsiednie źródłowe klatki według
rzeczywistego `deltaTime`. Ustawienie działa w tym samym `MotionState` dla MP4
i WebP, nie tworzy osobnego scheduler'a.

To pacing oryginalnych klatek, nie interpolacja optycznego przepływu. Nie
generuj w przeglądarce klatek mieszanych przez canvas/CSS: dla materiałów z
alfą tworzy to obwódki i smugi, a dla 1080p zwykle zwiększa koszt GPU ponad
budżet 16,67 ms. Jeśli projekt rzeczywiście wymaga nowych klatek, wygeneruj je
offline i dostarcz jako materiał źródłowy 60 FPS.

Diagnostyka udostępnia `data-motion-tail-pacing-steps` oraz
`motion.tailPacingSteps`. Po domknięciu `renderedProgress` musi być równy
`targetProgress`, prędkość musi wynosić zero, a sekwencja klatek nie może wykonać
kroku w przeciwnym kierunku.

### 4. Rejestracja i cleanup

Publiczny kontrakt:

```js
const unregister = window.GicleeScrollFrameCanvas.registerElement(
  '.media-block--scroll-scrub',
  {
    id: 'stable-element-id',
    initialize() {},
    setTargetProgress(rawProgress) {},
    render(context) {
      // context: now, deltaTime, globalProgress, targetProgress,
      // renderedProgress, reducedMotion, viewportWidth/Height, devicePixelRatio
    },
    activate() {},
    deactivate() {},
    destroy() {}
  }
);

// Przy demontażu:
unregister();
```

`registerElement` dołącza obiekt do istniejącego kontrolera i schedulera.
Zwrócona funkcja wykonuje `deactivate()` oraz `destroy()`. W `destroy` odłącz
własne obserwatory, anuluj fetch, zwolnij Object URL i zamknij `ImageBitmap`.

## Przykład 1: DOM bez dodatkowego JavaScript

To jest preferowany wzorzec dla prostego `transform` i `opacity`. Runtime sam
znajduje elementy wewnątrz root:

```html
<div
  data-scroll-animate
  data-scroll-animation-id="artwork-title"
  data-scroll-start="0.20"
  data-scroll-end="0.45"
  data-scroll-opacity="0,1"
  data-scroll-translate-y="40,0"
  data-scroll-scale="0.98,1"
  data-scroll-rotate="0,0"
  data-scroll-easing="ease-out"
>
  Tytuł dzieła
</div>
```

Dostępne pary: `data-scroll-opacity`, `data-scroll-translate-x`,
`data-scroll-translate-y`, `data-scroll-scale`, `data-scroll-rotate`.
Wartości są zapisywane tylko przy zmianie lokalnego postępu.

## Przykład 2: WebP 60 FPS z alfą

Nie twórz drugiego canvas renderera. Przygotuj zasób przez
`video_sequence.py`, następnie użyj istniejącego DOM:

```liquid
<canvas
  data-scroll-frame-canvas
  data-frame-manifest="{{ 'giclee-philosophy-1080-manifest.json' | asset_url }}"
  data-frame-quality="1080p"
  data-frame-fps="60"
  data-source-has-alpha="true"
  data-alpha-mode="straight"
  aria-hidden="true"
></canvas>
```

Manifest musi podawać wszystkie klatki, np.:

```json
{
  "version": 5,
  "frameCount": 210,
  "width": 1920,
  "height": 1080,
  "fps": 60,
  "codec": "webp",
  "pixelFormat": "rgba",
  "hasAlpha": true,
  "alphaMode": "straight",
  "fullSourceFrameUse": true
}
```

`ScrollFrameCanvas` zapewnia target-first queue, ograniczony LRU, cache HTTP,
`createImageBitmap`, `globalCompositeOperation='copy'`, cleanup i diagnostykę.
Nie dodawaj crossfade’u. Po zmianie wymiarów sprawdź skalowanie, DPR, jasne,
ciemne i kontrastowe tło oraz smugi.

## Przykład 3: warstwa zsynchronizowana

```js
const layer = document.querySelector('[data-artwork-glow]');

const unregisterGlow = window.GicleeScrollFrameCanvas.registerElement(
  layer.closest('.media-block--scroll-scrub'),
  {
    id: 'artwork-glow',
    last: -1,
    render(context) {
      const local = window.GicleeScrollFrameCanvas.mapProgress(
        context.renderedProgress,
        0.42,
        0.78
      );
      if (Math.abs(local - this.last) < 0.0001) return;
      this.last = local;
      layer.style.opacity = String(local);
      layer.style.transform = `translate3d(0, ${20 * (1 - local)}px, 0)`;
    },
    destroy() {
      layer.style.removeProperty('opacity');
      layer.style.removeProperty('transform');
    }
  }
);
```

Ta warstwa nie ma listenera ani RAF. Używa `renderedProgress`, więc nie rozjeżdża
się z filmem/klatkami.

## MP4, WebP i fallbacki

### MP4

Używaj istniejącego `ScrollNativeVideo`. Scroll tylko zmienia cel, kontroler
utrzymuje pojedynczy najnowszy seek. Materiał scrollowany powinien mieć GOP=1.
H.264 MP4 nie zachowuje alfy; jeśli źródło ma alfę, manifest musi jawnie
określić tło i `fallbackActive`. Fallback: przygotowany MP4 720p albo poster.

### WebP

Używaj `ScrollFrameCanvas`. Nie pobieraj całej sekwencji przy starcie.
Priorytet: cel, kierunek ruchu, sąsiednie klatki. Cache musi pozostać ograniczony,
a nieaktualne żądania muszą być odrzucone/ignorowane. Fallback: 720p lub poster.

Żaden fallback nie może zostawić pustej sekcji, zablokować scrolla, utworzyć
nieskończonych retry ani niejawnie spłaszczyć alfy na przypadkowym tle.

## Kanał alfa

- Sprawdź FFprobe i piksele próbki/całości; rozszerzenie nie jest dowodem.
- Nie konwertuj RGBA do JPEG i nie spłaszczaj na bieli/czerni bez jawnego
  fallbacku.
- Zachowaj piksele częściowo transparentne, miękkie krawędzie, cienie i poświaty.
- Canvas musi mieć `alpha:true`; nowa klatka musi zastąpić poprzednią bez duchów.
- Nie zmieniaj premultiplikacji bez kontroli dekodowania, canvasu i kompozycji.
- Testuj na tle jasnym, ciemnym i kontrastowym oraz sprawdź czarne/białe halo.
- Dla filmu sprawdź kodek i wsparcie przeglądarek. H.264 nie jest formatem alfa.

## Materiał 60 FPS

- Zapisz FPS i liczbę klatek w manifeście.
- Nie zaokrąglaj czasu do 1/30 s i nie wybieraj co drugiej klatki.
- Używaj `deltaTime`, centralnego RAF i najnowszego celu.
- Mierz osobno FPS strony, unikalne klatki, pominięcia, dekodowanie, kolejkę,
  główny wątek i częstotliwość monitora.
- Nie deklaruj pełnych 60 unikalnych klatek tylko dlatego, że RAF działa przy
  około 60 Hz.

## Wydajność

Preferuj `transform`, `opacity`, canvas i WebGL. Unikaj animowania `width`,
`height`, `top`, `left`, `margin`, `padding` i ciężkich filtrów. `will-change`
stosuj czasowo i usuwaj w cleanupie. Sprawdź layout thrashing, pamięć GPU i
stacking context.

Źródło krytyczne może inicjalizować się przed viewportem; zasób daleko poniżej
nie może ładować się w całości przy otwarciu. Nie pobieraj tego samego pliku
wielokrotnie. Na mobile ogranicz cache/dekodowanie, sprawdź szybki gest, obrót,
DPR, resize i natywną bezwładność scrolla.

## Accessibility i reduced motion

Treść musi być czytelna bez animacji. Uwzględnij `prefers-reduced-motion`,
wyłącz agresywną bezwładność/spring, unikaj migotania i błysków, nie blokuj
interakcji. Element dekoracyjny nie może być konieczny do zrozumienia strony.

## Diagnostyka i testy

Uruchom `?giclee_frames_debug=1`, opcjonalnie
`&giclee_motion_preset=direct`, `&giclee_alpha_debug=1` lub
`&giclee_reduced_motion=1`. Odczytaj:

```js
window.GicleeScrollFrameCanvas.diagnostics()
```

Sprawdź powolny i szybki scroll, zmianę kierunku, zatrzymanie, wielokrotne
wejście/wyjście, hot reload, brak ustawień legacy, błędne źródło, stan przed
metadanymi, wolną sieć, desktop/mobile, 60/120 Hz i spadki FPS. Rozdziel testy
automatyczne, przeglądarkowe, manualne i niewykonane na prawdziwym sprzęcie.

## Lista kontrolna dla AI

### Przed implementacją

- [ ] Przeczytałem dokumentację kanoniczną.
- [ ] Znalazłem aktualny silnik animacji.
- [ ] Sprawdziłem, czy podobny element już istnieje.
- [ ] Określiłem typ elementu.
- [ ] Sprawdziłem FPS.
- [ ] Sprawdziłem kanał alfa.
- [ ] Określiłem fallback.
- [ ] Określiłem zakres postępu.
- [ ] Sprawdziłem wymagania mobile.
- [ ] Nie tworzę równoległego systemu bez uzasadnienia.

### Podczas implementacji

- [ ] Korzystam ze wspólnego postępu.
- [ ] Korzystam z istniejącego scheduler’a.
- [ ] Obliczenia są niezależne od FPS.
- [ ] Nie wykonuję ciężkiej pracy bezpośrednio w `scroll`.
- [ ] Nie aktualizuję DOM lub zasobu, gdy wartość się nie zmieniła.
- [ ] Zachowuję kanał alfa.
- [ ] Nie ograniczam materiału 60 FPS do 30 FPS.
- [ ] Element można zatrzymać i wyczyścić.
- [ ] Konfiguracja jest walidowana.
- [ ] Zachowuję kompatybilność wsteczną.

### Po implementacji

- [ ] Przetestowałem powolny scroll.
- [ ] Przetestowałem szybki scroll.
- [ ] Przetestowałem zmianę kierunku.
- [ ] Przetestowałem mobile.
- [ ] Przetestowałem reduced motion.
- [ ] Przetestowałem jasne i ciemne tło.
- [ ] Przetestowałem kanał alfa.
- [ ] Sprawdziłem liczbę unikalnych klatek.
- [ ] Sprawdziłem błędy konsoli.
- [ ] Sprawdziłem wycieki listenerów i RAF.
- [ ] Zaktualizowałem dokumentację.
- [ ] Opisałem nowe ustawienia i fallback.

## Szablon polecenia dla kolejnego AI

```text
Dodaj do istniejącego systemu Film-scroll nowy animowany element.

Najpierw przeczytaj:

C:\Projekty\GicleeArt\docs\Film-scroll.md
C:\Projekty\GicleeArt\docs\Film-scroll-AI-Integration-Guide.md

Nie twórz równoległego systemu animacji. Wykorzystaj istniejący mechanizm postępu, easingów, smoothingu, scheduler renderowania, preload, diagnostykę i cleanup.

Element:
[OPIS ELEMENTU]

Źródło:
[PLIK LUB ŚCIEŻKA]

Typ:
[DOM / MP4 / WEBP SEQUENCE / CANVAS / WEBGL / INNY]

Zakres działania:
[NP. 20–65% POSTĘPU SEKCJI]

FPS:
[NP. 60 FPS / BRAK ZASTOSOWANIA]

Kanał alfa:
[TAK / NIE / SPRAWDŹ AUTOMATYCZNIE]

Sposób animacji:
[NP. PRZESUNIĘCIE, SKALA, OBRÓT, OPACITY, SYNCHRONIZACJA Z FILMEM]

Oczekiwany charakter:
[NP. DELIKATNY LUKSUSOWY / FILMOWY / DYNAMICZNY]

Wymagania:
- zachowaj pełną płynność materiału 60 FPS,
- zachowaj kanał alfa w całym pipeline,
- nie spłaszczaj przezroczystości,
- zapewnij fallback,
- uwzględnij mobile i prefers-reduced-motion,
- nie twórz osobnego listenera scroll i osobnej pętli RAF bez uzasadnienia,
- dodaj walidację, testy i diagnostykę,
- zaktualizuj dokumentację kanoniczną.

Na końcu przedstaw:
- zmienione pliki,
- sposób integracji z istniejącym systemem,
- model konfiguracji,
- wyniki testów,
- wpływ na wydajność,
- zachowanie kanału alfa,
- rzeczywistą płynność i liczbę unikalnych klatek,
- użyty fallback.
```

## Historia zmian

| Data | Autor | Zmiana | Kompatybilność |
|---|---|---|---|
| 2026-07-27 | Codex | Centralny scheduler, pełny model ruchu i presety, adaptery MP4/WebP, bounded preload/cache, alfa, 60 FPS, diagnostyka, deklaratywny DOM i publiczna rejestracja | Zachowane fallbacki dla starszych ustawień; brak destrukcyjnej migracji |
