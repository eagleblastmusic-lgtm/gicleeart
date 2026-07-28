# Film-scroll — kanoniczny system animacji sterowanej scrollem

> Słowa kluczowe dla AI: `Film-scroll`, `scroll scrub`, `MP4 seek`,
> `WebP frame sequence`, `60 FPS`, `alpha`, `GicleeApp`.
>
> Instrukcja rozszerzania systemu:
> [`Film-scroll-AI-Integration-Guide.md`](Film-scroll-AI-Integration-Guide.md).

Ten dokument jest źródłem prawdy dla istniejącego systemu Film-scroll.
Implementacją referencyjną jest sekcja **Filozofia marki**. System ma jeden
centralny scheduler `requestAnimationFrame`, wspólny model ruchu i dwa adaptery:
MP4 oraz sekwencję WebP.

## Rzeczywista mapa architektury

| Obszar | Plik | Odpowiedzialność |
|---|---|---|
| Panel GicleeApp | `cursor-api/Komponenty/filozofiamarki/gui.py` | Edytor strony, wybór MP4/WebP i 720p/1080p, przygotowanie zasobów, status FPS/alfa/fallbacku |
| Rejestr pól | `cursor-api/Komponenty/filozofiamarki/registry.py` | Sekcje „Charakter odtwarzania” i „Przezroczystość i tło”, zakresy, opisy, presety |
| Wspólny edytor | `cursor-api/Komponenty/_shared/theme_page_editor/types.py`, `gui_shell.py` | Model pól, zastosowanie całego presetu, wykrycie ustawień własnych, przycisk przywracania |
| Katalog i walidacja | `cursor-api/Komponenty/filozofiamarki/motion_config.py` | Odczyt katalogu, mapowanie pól, rekomendowany preset, walidacja |
| Presety runtime | `assets/giclee-scroll-motion-presets.json` | Jedno źródło dokładnych wartości dla GicleeApp i przeglądarki |
| Schema Shopify | `blocks/_media-without-appearance.liquid` | Serializowane ustawienia motywu i wartości domyślne |
| DOM i konfiguracja | `snippets/media.liquid` | Wybór jednego adaptera, `data-*`, manifesty, poster i warstwy tekstowe |
| Generowanie | `cursor-api/Komponenty/filozofiamarki/video_sequence.py` | FFprobe, FFmpeg, WebP/MP4, metadane, alfa, backupy |
| Runtime | `assets/giclee-scroll-scrub-video.js` | Postęp, easing, smoothing, scheduler, MP4, WebP, preload/cache i diagnostyka |
| Dane strony | `templates/page.filozofia-marki.json`, `cursor-api/Komponenty/filozofiamarki/variants/*.json` | Bieżący profil instancji sekcji |

Nie należy tworzyć drugiego listenera scroll, pętli RAF ani osobnego modelu
postępu dla elementu należącego do Film-scroll.

## Warianty źródła

| Adapter | 720p | 1080p | Alfa |
|---|---|---|---|
| Klatki | WebP RGBA 1280×720 | WebP RGBA HQ 1920×1080 | zachowywana |
| Film | H.264 MP4 1280×720 | H.264 MP4 1920×1080 | H.264 nie zachowuje; jawny fallback na tło |

Profil ruchu należy do instancji sekcji, więc zmiana 720p ↔ 1080p nie zmienia
charakteru animacji. Pola techniczne adapterów pozostają częścią tego samego
profilu, ale MP4 i WebP interpretują je zgodnie ze swoim sposobem renderowania.

## Model konfiguracji

### Ustawienia semantyczne

| Ustawienie Shopify | Znaczenie | Bezpieczny zakres |
|---|---|---|
| `scroll_motion_preset` | identyfikator presetu lub `custom` | katalog presetów |
| `scroll_motion_speed` | tempo mapowania; końce zawsze pozostają 0 i 1 | 0,25–3,00 |
| `scroll_motion_easing` | krzywa postępu | lista easingów |
| `scroll_motion_bezier` | `x1,y1,x2,y2`; x musi należeć do 0–1 | 4 liczby |
| `scroll_motion_smoothing_ms` | czas dochodzenia wartości renderowanej | 0–1000 ms |
| `scroll_motion_lag_ms` | filtr celu, bez timerów i kolejek zdarzeń | 0–500 ms |
| `scroll_motion_inertia` | domieszka prędkości celu | 0–100% |
| `scroll_motion_damping` | tłumienie modelu prędkości/sprężyny | 0–100% |
| `scroll_motion_max_catchup` | limit zmiany postępu na sekundę; 0 = bez limitu | 0–8 |
| `scroll_motion_stop_behavior` | `immediate`, `reach`, `nearest-frame`, `decelerate`, `snap` | lista |
| `scroll_motion_snap_points` | liczba równych punktów snap | 2–20 |
| `scroll_motion_direction` | `normal` lub `reverse` | lista |
| `scroll_motion_material_start/end` | fragment źródła kontrolowany scrollem | 0–100%, koniec > początek |
| `scroll_motion_interpolation` | `none`, `linear`, `exponential`, `damp`, `spring`, `velocity` | lista |
| `scroll_motion_tail_pacing` | równe odmierzanie źródłowych klatek w końcowej fazie hamowania | włącz/wyłącz |
| `scroll_motion_tail_window_frames` | odległość od celu, od której działa końcowe pacing | 2–30 klatek |

### Ustawienia techniczne

| Ustawienie Shopify | Adapter | Znaczenie |
|---|---|---|
| `scroll_motion_frame_rounding` | WebP | `floor`, `round` lub `ceil` |
| `scroll_motion_mp4_dead_zone_ms` | MP4 | minimalna różnica czasu przed nowym seekiem, 0–100 ms |
| `scroll_motion_webp_dead_zone_frames` | WebP | minimalna zmiana indeksu, 0–10 klatek |
| `scroll_motion_preload_radius` | WebP | logiczny promień preloadu, 2–60 |
| `scroll_motion_cache_frames` | WebP | limit bitmap; 0 = dobór automatyczny, 0–120 |
| `scroll_preserve_alpha` | WebP/manifest | oczekiwane zachowanie alfy |
| `scroll_force_transparent` | WebP | błąd zamiast niejawnego spłaszczenia, gdy brak alfy |
| `scroll_background_mode/value` | oba | `auto`, `transparent`, `color`, `gradient`, `image` i wartość |
| `scroll_alpha_diagnostics` | oba | checkerboard i dane diagnostyczne |

Wartości są serializowane w ustawieniach bloku Shopify. Brak nowych pól w
starszej konfiguracji jest obsługiwany przez katalog i fallbacki runtime.
Wartości `null`, `undefined`, `NaN` i wyjścia poza zakres są normalizowane.
Nie wykonano destrukcyjnej migracji ani czterokrotnego duplikowania profilu.

## Kolejność obliczeń

1. Listener `scroll` zapisuje tylko `scrollY`, czas wejścia i prosi centralny
   scheduler o klatkę.
2. Kontroler oblicza postęp sekcji. Materiał kończy się przy 80% drogi sekcji,
   a pozostałe 20% jest przeznaczone na końcową narrację.
3. Tempo mapuje wartość jako `p ** (1 / speed)` z zachowaniem dokładnych końców.
4. Nakładany jest wybrany easing, kierunek i zakres materiału.
5. Powstaje `rawProgress`.
6. Lag filtruje najnowszy cel wykładniczo i tworzy `targetProgress`; nie istnieje
   kolejka dawnych zdarzeń.
7. Interpolator, smoothing, bezwładność, damping i limit nadrabiania wyliczają
   `renderedProgress` na podstawie `deltaTime`.
   Gdy scroll już się zatrzymał i do celu zostało nie więcej niż
   `scroll_motion_tail_window_frames`, opcjonalny tail pacing odmierza przejście
   w tempie źródłowego FPS. Dla materiału 60 FPS oznacza to maksymalnie jedną
   źródłową klatkę na każde 16,67 ms przy ekranie 60 Hz.
   Poza jawnym trybem `spring` wynik jest ograniczony do odcinka między
   poprzednią wartością a bieżącym celem. Zapobiega to przestrzeleniu celu
   i widocznemu cofnięciu jednej lub kilku klatek po zatrzymaniu scrolla.
8. Po 90 ms bez wejścia działa wybrane zachowanie zatrzymania. Po maksymalnie
   1200 ms kontroler domyka małą pozostałą różnicę, aby nie „sunął” bez końca.
9. Adapter MP4 albo WebP renderuje tylko wtedy, gdy wynik faktycznie się zmienił.
10. Elementy dodatkowe otrzymują ten sam kontekst z `globalProgress`,
    `targetProgress` i `renderedProgress`.

`rawProgress` służy do natychmiastowej reakcji interfejsu. Element, który ma
poruszać się razem z obrazem, musi używać `renderedProgress`.

### Easing, smoothing, lag i bezwładność

- **Easing** zmienia geometryczne tempo na osi 0–1, ale nie tworzy opóźnienia.
- **Smoothing** określa, jak szybko obraz dochodzi do celu; jest oparty na czasie,
  nie na stałym współczynniku zależnym od FPS.
- **Lag** filtruje sam cel. Nie używa `setTimeout`.
- **Bezwładność** wykorzystuje prędkość celu, aby ruch miękko reagował na zmianę
  tempa i kierunku. Damping zapobiega trwałemu oscylowaniu.
- **Tail pacing** nie generuje nowych pikseli ani optycznego przepływu. W końcu
  hamowania równomiernie prezentuje sąsiednie, oryginalne klatki materiału.
  Eliminuje charakterystyczne „1–2 klatki, pauza, 1 klatka” bez ghostingu,
  smug i dodatkowego kosztu GPU typowego dla interpolacji obrazu.

## Dokładne wartości presetów

Katalog kanoniczny: `assets/giclee-scroll-motion-presets.json`. Skróty:
`speed / easing / smoothing / lag / inertia / damping / maxCatchUp /
stop / snap / direction / range / interpolation / rounding / MP4 dead zone /
WebP dead zone / preload / cache / tail pacing / tail window`.

| Preset (`id`) | speed | easing | smoothing | lag | inertia | damping | max | stop | snap |
|---|---:|---|---:|---:|---:|---:|---:|---|---:|
| Bezpośredni 1:1 (`direct`) | 1,00 | linear | 0 | 0 | 0 | 100 | 0 | immediate | 5 |
| Precyzyjny produktowy (`product`) | 1,00 | smootherstep | 100 | 0 | 4 | 92 | 6,00 | reach | 5 |
| Płynny (`smooth`) | 1,00 | sine-in-out | 220 | 15 | 18 | 86 | 3,00 | reach | 5 |
| Filmowy (`cinematic`) | 1,00 | cubic-in-out | 380 | 45 | 38 | 82 | 1,60 | decelerate | 5 |
| Miękka bezwładność (`soft-inertia`) | 1,00 | sine-in-out | 520 | 65 | 55 | 90 | 1,15 | decelerate | 5 |
| Dynamiczny (`dynamic`) | 1,15 | ease-out | 140 | 0 | 10 | 78 | 5,00 | reach | 5 |
| Ciężka kamera (`heavy-camera`) | 0,85 | cubic-in-out | 650 | 100 | 72 | 94 | 0,70 | decelerate | 5 |
| Delikatny luksusowy (`luxury`) | 0,95 | smootherstep | 240 | 20 | 16 | 92 | 1,80 | reach | 5 |

| Preset | kierunek | zakres | interpolacja | rounding | MP4 ms | WebP kl. | preload | cache |
|---|---|---|---|---|---:|---:|---:|---:|
| `direct` | normal | 0–100 | none | round | 4 | 1 | 12 | 0 |
| `product` | normal | 0–100 | damp | round | 6 | 1 | 14 | 0 |
| `smooth` | normal | 0–100 | exponential | round | 8 | 1 | 16 | 0 |
| `cinematic` | normal | 0–100 | damp | round | 8 | 1 | 18 | 0 |
| `soft-inertia` | normal | 0–100 | velocity | round | 10 | 1 | 18 | 0 |
| `dynamic` | normal | 0–100 | damp | round | 5 | 1 | 16 | 0 |
| `heavy-camera` | normal | 0–100 | spring | round | 12 | 1 | 14 | 0 |
| `luxury` | normal | 0–100 | damp | round | 8 | 1 | 18 | 0 |

| Preset | tail pacing | okno końcowe (kl.) |
|---|---|---:|
| `direct` | wyłączone | 12 |
| `product` | włączone | 10 |
| `smooth` | włączone | 12 |
| `cinematic` | włączone | 14 |
| `soft-inertia` | włączone | 16 |
| `dynamic` | włączone | 8 |
| `heavy-camera` | wyłączone | 12 |
| `luxury` | włączone | 12 |

Każdy preset używa Béziera `0.25,0.10,0.25,1.00`; jest on aktywny wyłącznie
dla ustawienia `custom-bezier`. Preset rekomendowany dla MP4, WebP i obecnej
strony Giclée Art to **Delikatny luksusowy (`luxury`)**.

Wybranie presetu ustawia wszystkie parametry. Ręczna zmiana przełącza panel na
`custom`, chyba że komplet wartości dokładnie odpowiada presetowi. Przycisk
**Przywróć zalecane ustawienia** przywraca rekomendację adaptera.

### Dodawanie presetu

1. Dodaj kompletny wpis ze wszystkimi 21 polami do
   `assets/giclee-scroll-motion-presets.json`.
2. Nie dodawaj drugiej kopii wartości w GUI — `motion_config.py` odczyta katalog.
3. Jeżeli preset ma być rekomendowany, zmień `recommended.video` lub
   `recommended.frames`.
4. Uruchom testy panelu, walidację JSON, test runtime obu adapterów i sprawdź
   dopasowanie `preset` ↔ `custom`.

## Adapter MP4

- Film jest pobierany raz do `Blob`; lokalny `blob:` omija problemy serwerów
  podglądu z zakresami `seekable`.
- Kontroler przechowuje tylko najnowszy żądany czas. Podczas aktywnego seeku nie
  buduje rosnącej kolejki.
- `currentTime` jest zmieniany dopiero po przekroczeniu martwej strefy.
- Czas końcowy to `duration - 1/fps`; nie ma kwantyzacji do 30 FPS.
- `requestVideoFrameCallback`, jeśli dostępny, mierzy zaprezentowane unikalne
  klatki, pominięcia i błędy seekowania.
- Manifest i metadane mają bezpieczne fallbacki przed `loadedmetadata`.

Generator używa H.264 CRF 10, `-preset slow`, `-g 1 -keyint_min 1
-sc_threshold 0 -movflags +faststart`. Każda klatka jest klatką kluczową.
Zwykły H.264 MP4 nie zachowuje alfy; materiał RGBA jest świadomie komponowany na
czerni, a manifest zapisuje `alphaLostDuringConversion` i `fallbackActive`.

## Adapter WebP

- `frame = rounding(renderedProgress * (frameCount - 1))`; brak sztucznego
  limitu 30 FPS i brak pomijania parzystych/nieparzystych klatek.
- Zmiana obrazu następuje tylko po zmianie indeksu i przekroczeniu dead zone.
- Klatka docelowa ma najwyższy priorytet. Nieaktualne oczekujące dekodowania
  dalej niż `2 × preloadRadius` są anulowane/ignorowane.
- LRU obejmuje bitmapy i blob cache. `ImageBitmap.close()` jest wykonywane przy
  eksmisji i cleanupie.
- Automatyczny cache bitmap 1080p: 8/12/16 dla pamięci ≤4/≤8/>8 GB; 720p:
  16/20/24. Dekodowanie ma współbieżność 1, aby ciężkie RGBA nie tworzyło
  skoków głównego wątku podczas szybkiego scrolla.
- Gorący preload dekoduje najwyżej
  `min(cache, 1 + max(1, ceil(preloadRadius/6)))` klatek po narysowaniu
  aktualnego celu, nie cały promień naraz.
- Canvas jest tworzony z `alpha:true`; bitmapa ma jawne
  `premultiplyAlpha:'premultiply'`, a `globalCompositeOperation='copy'`
  zastępuje poprzednią klatkę bez smug. Nie ma kosztownego crossfade’u.
- Manifest i obrazy korzystają z cache HTTP `force-cache`.

Generator WebP dekoduje WebM/VP9 przez `libvpx-vp9`, skaluje Lanczosem, zapisuje
RGBA z jakością 82 dla 720p i 95 dla 1080p. Jeżeli źródło ma alfę, a wynikowe
klatki jej nie mają, generowanie kończy się błędem.

## 60 FPS: zakres gwarancji

System przechowuje `fps`, `frameCount`, `sourceFps`, `sourceFrameCount` i
`fullSourceFrameUse`. Centralny RAF nie ma limitu 30 FPS, obliczenia używają
`deltaTime`, a oba adaptery mogą adresować wszystkie 210 klatek obecnego
materiału 60 FPS. To zachowuje **potencjał** 60 FPS.

Nie wolno jednak uznawać 60 wywołań RAF za dowód 60 unikalnych klatek obrazu.
Rzeczywista liczba zależy od tempa scrolla, monitora, przeglądarki, dekodera i
gotowości cache. W trybie debug należy raportować osobno `pageFps`,
`uniqueFramesLastSecond`, `skippedFrames`, kolejkę i czas renderowania.

## Alfa i kompozycja

- Obecność alfy wykrywa FFprobe oraz kontrola wygenerowanych obrazów; nie jest
  wnioskowana wyłącznie z rozszerzenia.
- Manifest rozróżnia alfę źródła i wynikowego zasobu oraz zapisuje jej tryb.
- WebP zachowuje pełną i częściową przezroczystość. Canvas nie jest wypełniany
  kolorem, chyba że jawnie wymusza to tło sekcji.
- `forceTransparent` blokuje nieprzezroczystą sekwencję i H.264 MP4.
- Tło może być automatyczne, transparentne, kolorem, gradientem lub obrazem.
- Diagnostykę krawędzi uruchamia `giclee_alpha_debug=1`; checkerboard pomaga
  wykryć spłaszczenie i czarne/białe obwódki.
- `premultiplyAlpha` jest jawne w dekoderze. Nie należy zmieniać modelu
  premultiplikacji bez testów całego pipeline.

## Lazy load, scheduler i cleanup

`IntersectionObserver` z marginesem 75% inicjalizuje źródło przed wejściem, ale
zatrzymuje ciągłą pracę poza sekcją. `ResizeObserver` zleca wspólny pomiar.
Jeden listener scroll wyłącznie aktualizuje cele. MutationObserver obsługuje
Shopify hot reload bez podwójnej inicjalizacji.

Cleanup abortuje fetch, odłącza obserwatory, usuwa elementy dodatkowe, zwalnia
URL obiektu i bitmapy. Runtime nie używa `setTimeout` ani `setInterval`.

## Reduced motion i mobile

Przy `prefers-reduced-motion` lag i inertia są zerowane, smoothing ograniczany
do 80 ms, a `spring`/`velocity` przechodzą na stabilne `exponential`. Zawartość
pozostaje widoczna. Mobile korzysta z tego samego modelu, ale automatycznie
ogranicza cache i współbieżność według `navigator.deviceMemory`.

Nie ma osobnego profilu breakpointów, ponieważ obecny model strony go nie
wymaga. Rzeczywiste urządzenia mobilne, obrót ekranu i wysokie DPR trzeba
sprawdzać przed publikacją nowego ciężkiego materiału.

## Diagnostyka

Parametry URL:

- `giclee_frames_debug=1` — dane ruchu, adaptera, FPS i cache w `data-*`;
- `giclee_motion_preset=<id>` — niedestrukcyjne nadpisanie presetu;
- `giclee_alpha_debug=1` — checkerboard i diagnostyka alfy;
- `giclee_reduced_motion=1` — wymuszenie profilu reduced motion.

API:

```js
window.GicleeScrollFrameCanvas.diagnostics();
window.GicleeScrollFrameCanvas.presets();
window.GicleeScrollFrameCanvas.refresh();
```

Najważniejsze dane: `rawProgress`, `targetProgress`, `renderedProgress`,
`pageFps`, `pageWorstFrameMs`, `uniqueFramesLastSecond`, `skippedFrames`,
`seekExecuted/Skipped/Errors`, `targetFrame`, `renderedFrame`,
`decodeQueue`, `decodeFailures`, `bitmapCache`, `frameRenderMs`,
`averageFrameRenderMs`, `pageAverageFrameMs`, `rafHz`,
`sourceFps`, `sourceFrameCount`, `hasAlpha`, `alphaMode`.

## Zasady wydajności i jakości

- Animuj `transform` i `opacity`; unikaj layoutu w każdej klatce.
- Nie trzymaj jednocześnie kontrolera MP4 i WebP w jednej instancji.
- Nie ustawiaj `currentTime` ani nie dekoduj obrazu bez zmiany celu.
- Dla MP4 scrollowanego używaj częstych keyframe’ów; referencja ma GOP=1.
- Nie używaj JPEG dla sekwencji z alfą ani przy wymaganej zgodności kolorów.
- Poster pozostaje widoczny do gotowości pierwszej klatki.
- Błąd źródła pokazuje poster/fallback, nie pustą sekcję i nie blokuje scrolla.
- Podmiana zasobów tworzy rotacyjny backup; zachowywane są trzy ostatnie.

## Rozszerzanie systemu

Proste elementy DOM opisuj przez `data-scroll-animate`. Bardziej złożone
rejestruj przez `window.GicleeScrollFrameCanvas.registerElement(...)`.
Wzorce, kontrakt cyklu życia, checklisty, alfa, 60 FPS i trzy działające
przykłady zawiera
[`Film-scroll-AI-Integration-Guide.md`](Film-scroll-AI-Integration-Guide.md).
