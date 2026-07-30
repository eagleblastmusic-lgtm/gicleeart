# Film-scroll — kanoniczny system animacji sterowanej scrollem

> Słowa kluczowe dla AI: `Film-scroll`, `scroll scrub`, `MP4 seek`,
> `WebM passthrough`, `WebP frame sequence`, `60 FPS`, `alpha`, `GicleeApp`.

Ten dokument jest źródłem prawdy dla istniejącego systemu Film-scroll.
Implementacją referencyjną jest sekcja **Filozofia marki**. System ma jeden
centralny scheduler `requestAnimationFrame`, wspólny model ruchu i dwa adaptery:
natywny film (`MP4`/`WebM`) oraz sekwencję WebP.

## Kontrakt polecenia „wstaw moduł Film-scroll”

Polecenia `wstaw moduł Film-scroll`, `dodaj Film-scroll` i oczywista literówka
`Fillm-scroll` oznaczają **całą funkcję**, a nie samo wstawienie filmu do
Liquid. AI ma wykonać wszystkie poniższe warstwy:

1. dodać na wskazanej stronie nową instancję sekcji/bloku Film-scroll,
   korzystającą ze wspólnego runtime;
2. dodać dla tej instancji osobną, widoczną sekcję w edytorze **GicleeApp**,
   wzorowaną na sekcjach `scroll_story` / `scroll_story_wrota` z komponentu
   **Filozofia marki**; w `scroll_story` i `scroll_story_wrota` ustawienia
   ruchu są zwijanym akordeonem **Charakter odtwarzania**, a nie osobną
   pozycją listy;
3. podłączyć wybór źródła, kontenera, jakości i konkretnego pliku oraz ustawienia
   ruchu; każda instancja ma jedną własną sekcję, a w niej zwijany przycisk
   **Charakter odtwarzania**;
4. zapewnić rodzinę zasobów, stabilne sloty runtime, aktywację pliku po zapisie
   i selektywny deploy;
5. sprawdzić ruch w dół, ruch w górę, zmianę kierunku, zatrzymanie i ponowne
   wejście do sekcji.

Nie wolno uznać zadania za wykonane po dodaniu samego HTML/Liquid, samego pola
w schemacie Shopify albo samej kontrolki GicleeApp. Nie wolno zmieniać WebM na
MP4 jako sposobu naprawy, jeśli użytkownik wprost o to nie poprosił.

Jeżeli strona lub miejsce nie zostały wymienione w zdaniu, należy użyć
bieżącego kontekstu zadania. Pytanie doprecyzowujące jest potrzebne dopiero
wtedy, gdy repozytorium nie wskazuje jednoznacznie strony docelowej.

W edytorach ze wspólnym panelem **Sekcje strony** operator może też kliknąć
PPM na liście i wybrać **Dodaj „Scroll Film”…**. Nowa instancja jest wstawiana
za klikniętą sekcją, otrzymuje własne źródło i ustawienia, a przycisk
**Charakter odtwarzania** rozwija parametry ruchu bez dodawania drugiej pozycji
na liście. Specjalny panel RAM strony Giclée Frame kieruje tę samą akcję do
właściwego, zapisywalnego edytora szablonu. Nowa sekcja pozostaje wyłączona,
dopóki film nie zostanie poprawnie przygotowany; udany import włącza ją
automatycznie. Samodzielny Scroll Film wypełnia viewport od jego górnej
krawędzi (`top: 0`) i nie dziedziczy rezerwy nagłówka ani pasa separatora
referencyjnej sceny „Filozofia marki”.

### Obowiązkowa ścieżka implementacji

| Warstwa | Co trzeba zrobić |
|---|---|
| Szablon Shopify | Dodać sekcję/blok w `templates/page.<nazwa>.json`; referencją jest `_media-without-appearance` w `page.filozofia-marki.json`. |
| Schema i Liquid | Użyć pól `scroll_*` z `blocks/_media-without-appearance.liquid` i konfiguracji `data-*` z `snippets/media.liquid`; nie kopiować runtime. |
| GicleeApp | Dodać osobny `TemplateZone` Film-scroll. Ustawienia ruchu umieścić w zwijanej grupie/przycisku **Charakter odtwarzania** wewnątrz tej strefy; wspólne edytory robią to przez menu PPM. |
| Panel i zapis | W `gui.py` zarejestrować strefy, callback `after_template_save` oraz ścieżki aktywnych zasobów do deployu. |
| Biblioteka plików | W `video_sequence.py` dodać rodzinę w `ASSET_FAMILIES` albo bezpiecznie uogólnić ten mechanizm; nie przypisywać nowej instancji domyślnie do `philosophy`. |
| Stabilny asset | Rozszerzyć mapowanie w `snippets/media.liquid`, aby wybrany pakiet został zmaterializowany do jednoznacznego slotu używanego przez frontend. |
| Runtime | Ładować `assets/giclee-scroll-scrub-video.js` tylko raz i używać istniejącego `CentralScheduler`; zewnętrzny runway przekazuje postęp przez `setProgress`. |
| Testy | Dodać regresję konfiguracji i test przeglądarkowy: dół → góra → dół, bez restartu materiału i bez lawiny seeków. |

### Definition of done

Moduł jest gotowy dopiero, gdy:

- jego sekcja istnieje w szablonie i renderuje się na właściwej stronie;
- GicleeApp pokazuje nową, nazwaną sekcję z przyciskiem **Charakter
  odtwarzania** i zapisuje ustawienia do właściwego `section_id`/bloku, bez
  nadpisywania innej instancji;
- wybrany plik jest aktywowany po zapisie i znajduje się na liście deployu;
- frontend oraz aktywny wariant GicleeApp mają te same wartości;
- WebM pozostaje WebM, jeśli taki kontener wybrał użytkownik;
- test przewijania w obu kierunkach przechodzi po zimnym i ciepłym ładowaniu;
- dokumentacja nadal wskazuje ten plik jako jedyne źródło prawdy.

## Rzeczywista mapa architektury

| Obszar | Plik | Odpowiedzialność |
|---|---|---|
| Panel GicleeApp | `cursor-api/Komponenty/filozofiamarki/gui.py` | Edytor strony, wybór MP4/gotowego WebM/WebP, 720p/1080p i konkretnego pliku z filtrowanej biblioteki; przygotowanie zasobów, status FPS/alfa/GOP/fallbacku |
| Rejestr pól | `cursor-api/Komponenty/filozofiamarki/registry.py` | Zwijane grupy „Charakter odtwarzania” i „Ustawienia tła” wewnątrz sekcji Film-scroll, zakresy, opisy, presety |
| Wspólny edytor | `cursor-api/Komponenty/_shared/theme_page_editor/types.py`, `gui_shell.py` | Model pól, zastosowanie całego presetu, wykrycie ustawień własnych, przycisk przywracania |
| Katalog i walidacja | `cursor-api/Komponenty/filozofiamarki/motion_config.py` | Odczyt katalogu, mapowanie pól, rekomendowany preset, walidacja |
| Presety runtime | `assets/giclee-scroll-motion-presets.json` | Jedno źródło dokładnych wartości dla GicleeApp i przeglądarki |
| Schema Shopify | `blocks/_media-without-appearance.liquid` | Serializowane ustawienia motywu i wartości domyślne |
| DOM i konfiguracja | `snippets/media.liquid` | Wybór jednego adaptera, `data-*`, manifesty, poster i warstwy tekstowe |
| Generowanie | `cursor-api/Komponenty/filozofiamarki/video_sequence.py` | FFprobe, FFmpeg, WebP/MP4, WebM passthrough, metadane, alfa, GOP i backupy |
| Runtime | `assets/giclee-scroll-scrub-video.js` | Postęp, easing, smoothing, scheduler, natywny film MP4/WebM, WebP, preload/cache i diagnostyka |
| Dane strony | `templates/page.filozofia-marki.json`, `cursor-api/Komponenty/filozofiamarki/variants/*.json` | Bieżący profil instancji sekcji |

Nie należy tworzyć drugiego listenera scroll, pętli RAF ani osobnego modelu
postępu dla elementu należącego do Film-scroll.

## Warianty źródła

| Adapter | 720p | 1080p | Alfa |
|---|---|---|---|
| Klatki | WebP RGBA 1280×720 | WebP RGBA HQ 1920×1080 | zachowywana |
| Film MP4 | H.264 MP4 1280×720 | H.264 MP4 1920×1080 | H.264 nie zachowuje; jawny fallback na tło |
| Gotowy WebM | plik 1280×720 kopiowany 1:1 | plik 1920×1080 kopiowany 1:1 | zachowywana, jeśli potwierdzona przez metadane |

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
| `scroll_video_container` | natywny film | `mp4` albo `webm`; starsze dane domyślnie wybierają MP4 |
| `scroll_video_source` | natywny film / GicleeApp | identyfikator konkretnego pakietu bibliotecznego; pusta wartość oznacza dotychczasowy domyślny slot |
| `scroll_motion_frame_rounding` | WebP | `floor`, `round` lub `ceil` |
| `scroll_motion_mp4_dead_zone_ms` | MP4/WebM | minimalna różnica czasu przed nowym seekiem, 0–100 ms; identyfikator zachowany dla kompatybilności |
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

### Biblioteka konkretnych plików

Import filmu nadal aktualizuje stabilny slot runtime wymagany przez starsze
warianty, ale zapisuje też lokalny pakiet
`giclee-scroll-library-<rodzina>-<jakość>-<format>-<nazwa>-<hash>`.
Pakiet zawiera film, poster i manifest. Pole **Konkretny plik** jest dynamiczne:
filtruje po rodzinie (`philosophy`/`wrota`/`shared`), kontenerze i
rozdzielczości. Stabilny slot runtime jest technicznym fallbackiem i nie tworzy
drugiej widocznej pozycji: jeden materiał ma w selektorze dokładnie jeden wpis.

Po zapisaniu strony `apply_scroll_video_selection()` materializuje wybraną
pozycję do kanonicznych nazw runtime. Biblioteka pozostaje lokalna i jest
ignorowana przez theme sync, natomiast aktywny slot trafia do `theme dev` oraz
selektywnego deployu. Zapobiega to równoczesnemu przesyłaniu wielu dużych filmów
i zachowuje kompatybilność konfiguracji bez `scroll_video_source`.

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

## Adapter natywnego filmu: MP4 i WebM

- MP4 jest pobierany raz do `Blob`; lokalny `blob:` omija problemy serwerów
  podglądu z zakresami `seekable`.
- W lokalnym podglądzie (`localhost`, `127.0.0.1`, `::1`) również WebM jest
  pobierany do `Blob`, ponieważ Shopify Theme Dev może odpowiedzieć `200` na
  żądanie `Range` zamiast udostępnić niezawodne zakresy. W produkcji duży,
  nieprzezroczysty WebM pozostaje pod natywnym adresem CDN z `preload=auto`.
  WebM z alfą jest zawsze pobierany do buforowanego `Blob`, a dekoder dostaje
  krótki seek rozgrzewający i powrót do klatki 0.
- Kontroler przechowuje tylko najnowszy żądany czas. Podczas aktywnego seeku nie
  buduje rosnącej kolejki.
- `currentTime` jest zmieniany dopiero po przekroczeniu martwej strefy.
- Czas końcowy to `duration - 1/fps`; nie ma kwantyzacji do 30 FPS.
- `requestVideoFrameCallback`, jeśli dostępny, mierzy zaprezentowane unikalne
  klatki, pominięcia i błędy seekowania.
- Manifest i metadane mają bezpieczne fallbacki przed `loadedmetadata`.
- Ten sam kontroler, scheduler, seek i diagnostyka obsługują oba kontenery;
  zmiana formatu nie tworzy drugiego systemu animacji.
- Dla WebM z `intraOnly=false` ruch do przodu korzysta z hybrydy:
  pojedynczy seek z pre-rollem 80–140 ms, a następnie natywne `play()` ze
  współczynnikiem zależnym od profilu źródła. Nieprzezroczysty WebM jest
  dekodowany sekwencyjnie do driftu 320 ms. Dla VP9 alpha próg wynosi 550 ms,
  a przy GOP ≤ 15 — 1,25 s, ponieważ krótki odcinek `play()` jest w Chromium
  tańszy niż dokładny seek przez programowo dekodowaną alfę. Duży skok jest
  odraczany, dopóki wejście scroll jest aktywne, a po zatrzymaniu ten sam cel
  nie może wywoływać kolejnych dużych seeków. Cofanie wykonuje seek do
  najnowszego celu.
- Kierunek wynika ze zmiany celu scrolla względem poprzedniego celu, a nie z
  różnicy między celem i opóźnioną klatką dekodera. Warunek cofania musi być
  sprawdzony przed ścieżką `delta > 0`: cofnięty cel może nadal leżeć przed
  klatką prezentowaną, gdy film mocno pozostaje za scrollem.
- Nieprzezroczysty WebM może podczas doganiania użyć `playbackRate` 0,75–2,5.
  WebM z alfą korzysta z ostrożniejszego zakresu 0,25–1,0.
- Decyzje o doganianiu są oparte na `lastPresentedFrame` z
  `requestVideoFrameCallback`, a nie wyłącznie na `video.currentTime`.
  Zegar filmu może dojść do celu mimo tego, że przeglądarka nie wyświetliła
  klatek pośrednich.
- Sekcje sterowane zewnętrznym przebiegiem (obecnie portal Wrota po cytacie)
  wywołują `GicleeScrollFrameCanvas.setProgress(...)`. Nie zapisują
  `currentTime` w każdym zdarzeniu scroll i nadal używają centralnego
  schedulera.

Generator używa H.264 CRF 10, `-preset slow`, `-g 1 -keyint_min 1
-sc_threshold 0 -movflags +faststart`. Każda klatka jest klatką kluczową.
Zwykły H.264 MP4 nie zachowuje alfy; materiał RGBA jest świadomie komponowany na
czerni, a manifest zapisuje `alphaLostDuringConversion` i `fallbackActive`.

Tryb **Gotowy WebM — bez konwersji**:

- przyjmuje wyłącznie `.webm` o dokładnych wymiarach wybranego slotu jakości;
- kopiuje plik bajt w bajt do osobnego assetu runtime, bez ponownego kodowania;
- generuje tylko lekki poster WebP oraz manifest;
- zapisuje rzeczywiste `fps`, `frameCount`, kodek, format pikseli, alfę,
  `keyframeInterval`, `intraOnly`, `mimeType: video/webm` i
  `passthrough: true`;
- zachowuje przezroczystość WebM, jeżeli FFprobe/poster ją potwierdza;
- nie nadpisuje MP4 — oba kontenery i ich manifesty mogą istnieć równolegle.

WebM bez GOP=1 jest dozwolony, ale panel pokazuje największy wykryty odstęp
klatek kluczowych. Długi GOP może pogorszyć cofanie i szybki scrub; dla
najlepszej responsywności materiał powinien mieć klatkę kluczową na każdej
klatce.

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

Pokazanie 210 kolejnych klatek na monitorze 60 Hz wymaga co najmniej 3,5 s.
Przy rzeczywistych 55 Hz potrwa co najmniej około 3,82 s. Nie da się
jednocześnie pokazać wszystkich klatek, natychmiast dogonić dowolnie szybki
scroll i nie mieć lagu.

## Studium przypadku: pierwsza scena WebM 1080p z alfą

Pierwszy pomiar 2026-07-28 dotyczył pliku GOP 128. Aktualny materiał sprawdzony
2026-07-29:

- 1920×1080, 60 FPS, 210 klatek;
- VP9 WebM passthrough z zachowaną alfą;
- `keyframeInterval=15`, `intraOnly=false` — klatka kluczowa co 15 klatek,
  **nie** każda klatka;
- 2 145 498 bajtów;
- preset ruchu `direct`, bez smoothingu i lagu.

Pierwszą przyczyną pozornego braku poprawy był stary proces Shopify theme dev.
Plik i manifest na dysku miały GOP 15, lecz strona nadal pobierała poprzedni
hash assetu, a DOM raportował `keyframeInterval=128`. Zwykły reload nie
pomagał. Dopiero restart procesu na porcie 9292 zmienił parametr `?v=...`
manifestu i `data-keyframe-interval` na 15. Przed testem zawsze porównaj
wartości z DOM z plikiem na dysku; inaczej mierzysz inną wersję zasobu.

Po rzeczywistym wczytaniu GOP 15 pozostało ograniczenie dekodera. W
ustabilizowanym teście Chromium strona utrzymywała 59,5 FPS, lecz
`requestVideoFrameCallback` nadal raportował pominięcia obrazu VP9 1080p
alpha. Drugi WebM 1080p60 bez alfy działał płynniej mimo tego samego GOP 15.
Dominującą różnicą jest ciężka, zwykle programowa ścieżka dekodowania kanału
alfa. Wynik nie wyklucza udziału głównego wątku lub compositora, dlatego zawsze
sprawdzaj równocześnie `pageWorstFrameMs`.

To ograniczenie jest potwierdzone w źródłach Chromium: fabryka akceleracji GPU
odrzuca strumienie z `AlphaMode::kHasAlpha` (poza HEVC na macOS), a dekoder VP9
software rozpakowuje osobno obraz i `alpha_data` przez libvpx:
[GPU video accelerator](https://chromium.googlesource.com/chromium/src/media/+/9a33ea72d49026d40d7c3ebff13b26fe9d0aef9b/mojo/clients/mojo_gpu_video_accelerator_factories.cc),
[VpxVideoDecoder](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/media/filters/vpx_video_decoder.cc).
GOP 1 może skrócić seek, ale nie przełącza VP9 alpha na dekoder sprzętowy.

Aktualne zabezpieczenia runtime:

1. dla źródła alpha z GOP ≤ 15 ruch do przodu pozostaje sekwencyjny do driftu
   1,25 s, więc krótki poślizg nie uruchamia drogiego seeku;
2. `playbackRate` alpha jest ograniczony do zakresu 0,25–1,0×;
3. duży skok podczas aktywnego scrolla nie tworzy serii seeków;
4. po ustaniu wejścia pozostaje najwyżej jeden seek z pre-rollem 80–140 ms;
5. stan jest oceniany według ostatniej zaprezentowanej klatki;
6. WebM alpha jest buforowany do `Blob` i dostaje krótki prewarm seek; duży
   WebM bez alfy pozostaje pod natywnym URL w produkcji, a w lokalnym
   podglądzie także korzysta z `Blob`.

Rzeczywiście wykonany test przeglądarkowy 2026-07-29 po ustaniu równoległych
synchronizacji theme dev, Chromium, 8 natywnych impulsów wheel po 120 px:

- 59,5 FPS strony, najgorsza próbka 33,2 ms;
- bez forward seeku: `seekExecuted=0`, `largeForwardSeeks=0`;
- po domknięciu gestu `targetFrame=91`, `renderedFrame=91`;
- dekoder nadal zaraportował 22 pominięte klatki — nie ma dowodu 60
  unikalnych klatek obrazu alpha.

Wniosek: runtime nie tworzy kolejki seeków, a średnia diagnostyczna strony w
tym przebiegu wyniosła 59,5 FPS. Próbka 33,2 ms oznacza jednak co najmniej
jedno przekroczenie budżetu 16,67 ms, więc nie jest to dowód stałych 60 FPS.
Film dochodzi do celu, ale ten plik na tym dekoderze nie daje 60
prezentowanych klatek alpha. Dla kontroli kolejności każdego indeksu z alfą
wybierz sekwencję WebP i zweryfikuj ją na urządzeniu docelowym; dla natywnego
filmu zejdź do 720p alpha albo usuń alfę i użyj
nieprzezroczystego WebM/MP4. GOP 1 poprawia losowy scrub, lecz nie gwarantuje
sprzętowego dekodowania VP9 alpha.

## Alfa i kompozycja

- Obecność alfy wykrywa FFprobe oraz kontrola wygenerowanych obrazów; nie jest
  wnioskowana wyłącznie z rozszerzenia.
- Manifest rozróżnia alfę źródła i wynikowego zasobu oraz zapisuje jej tryb.
- WebP zachowuje pełną i częściową przezroczystość. Canvas nie jest wypełniany
  kolorem, chyba że jawnie wymusza to tło sekcji.
- `forceTransparent` blokuje nieprzezroczystą sekwencję i natywny film bez
  potwierdzonej alfy; przezroczysty WebM przechodzi tę kontrolę.
- Tło może być automatyczne, transparentne, kolorem, gradientem lub obrazem.
- Diagnostykę krawędzi uruchamia `giclee_alpha_debug=1`; checkerboard pomaga
  wykryć spłaszczenie i czarne/białe obwódki.
- `premultiplyAlpha` jest jawne w dekoderze. Nie należy zmieniać modelu
  premultiplikacji bez testów całego pipeline.
- Pary **Przed / Po** w Treści 3D Wrot używają `object-fit: contain`, a kontener
  przejmuje naturalne proporcje obrazu, aby oba pliki były widoczne w całości
  bez bocznych pasów. Jego limit rozmiaru jest dwukrotnie większy niż pierwotnie.
  Rzeczywisty rozmiar jest ograniczany dostępną wysokością viewportu po odjęciu
  paddingów sekcji i przeliczany po zmianie rozmiaru okna.
  Natywny suwak zakresu steruje wspólną granicą porównania myszką, dotykiem
  i klawiaturą; nie powstaje drugi listener scroll.

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
window.GicleeScrollFrameCanvas.setProgress(root, progress, { immediate: false });
```

Najważniejsze dane: `rawProgress`, `targetProgress`, `renderedProgress`,
`pageFps`, `pageWorstFrameMs`, `uniqueFramesLastSecond`, `skippedFrames`,
`seekExecuted/Skipped/Errors`, `targetFrame`, `renderedFrame`,
`decodeQueue`, `decodeFailures`, `bitmapCache`, `frameRenderMs`,
`averageFrameRenderMs`, `pageAverageFrameMs`, `rafHz`,
`sourceFps`, `sourceFrameCount`, `hasAlpha`, `alphaMode`,
`webmInterFrame`, `sequentialPlayback`, `sequentialPlaybackStarts`,
`sequentialPlaybackFrames`, `largeForwardSeeks`, `deferredForwardSeeks`,
`presentationRecoverySeeks`, `reverseSeeks`, `maxTargetDriftMs`,
`keyframeInterval`, `intraOnly`, `prewarmCompleted`, `sourceDelivery`,
`rvfcCallbackCount`, `rvfcPresentedFrames`, `rvfcCallbackGaps`,
`rvfcProcessingDurationP95Ms`, `rvfcMaxCallbackLatenessMs`,
`videoDroppedFrames`, `videoTotalFrames`.

`requestVideoFrameCallback` jest obserwatorem, nie wymusza prezentacji klatek.
Dla filmu zestawiaj jego dane z
`video.getVideoPlaybackQuality()`; dla canvasu rVFC nie ma zastosowania.
Specyfikacje:
[rVFC](https://wicg.github.io/video-rvfc/),
[Media Playback Quality](https://w3c.github.io/media-playback-quality/).

## Procedura diagnozy zacięć dla kolejnego AI

Nie zaczynaj od losowej zmiany easingów. Najpierw rozdziel cztery niezależne
warstwy: wejście scroll, model ruchu, scheduler strony i dekoder obrazu.

### 1. Ustal faktyczne źródło

Sprawdź aktywny blok w `templates/page.filozofia-marki.json`, a nie tylko pliki
obecne w `assets`. Zapisz:

- `scroll_video_engine`, `scroll_video_container`, jakość i konkretny
  `scroll_video_source`;
- rozdzielczość, FPS, liczbę klatek, kodek, format pikseli i alfę;
- `keyframeInterval`, `intraOnly`, `passthrough`;
- wielkość pliku i czas trwania;
- preset, smoothing, lag, inertia, dead zone i sposób scrolla strony.

Przykładowe kontrole:

```powershell
ffprobe -v error -select_streams v:0 -show_entries `
  stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames:stream_tags=alpha_mode `
  -of json "assets\plik.webm"

ffprobe -v error -select_streams v:0 -show_frames `
  -show_entries frame=key_frame,best_effort_timestamp_time `
  -of csv "assets\plik.webm"
```

Samo rozszerzenie `.webm`, deklaracja „60 FPS” albo obecność 210 klatek nie
oznacza, że przeglądarka potrafi je prezentować z częstotliwością 60 Hz.

### 2. Porównaj cel, zegar i klatkę prezentowaną

Włącz `?giclee_frames_debug=1` i obserwuj równocześnie:

- `pageFps` i `pageWorstFrameMs`;
- `targetFrame`;
- `renderedFrame`;
- `currentTime`;
- `uniqueFramesLastSecond` i `skippedFrames`;
- `seekExecuted`, `seeking`, `seekPending`;
- `maxTargetDriftMs`.

Interpretacja:

- `pageFps≈60`, ale `renderedFrame` skacze: problem dekodera lub sterowania
  filmem, nie głównego RAF;
- `currentTime≈cel`, ale `renderedFrame` pozostaje z tyłu: zegar odtwarzania
  wyrzuca klatki; nie używaj `currentTime` jako dowodu płynności;
- rosnące `seekExecuted` podczas jednego gestu: kilka systemów zapisuje
  `currentTime` albo brak koalescowania;
- duży `targetFrame-renderedFrame` po zatrzymaniu: za wysoki playback rate,
  zbyt długi lag albo kontroler przestał pracować po wyjściu z viewportu;
- `pageFps<50` i wysoki `pageWorstFrameMs`: szukaj pracy na głównym wątku,
  layout thrashingu, zbyt dużego canvasu/cache albo wielu schedulerów.

### 3. Testuj prawdziwy wheel, nie tylko End/PageDown

`End`, `PageDown`, drag scrollbara i duży syntetyczny skok są testami
granicznymi, ale nie odwzorowują serii impulsów kółka. Wykonaj osobno:

1. pojedynczy wheel 120 px i zatrzymanie;
2. 6–10 impulsów wheel 120 px co około 100–160 ms;
3. szybki duży gest;
4. zmianę kierunku;
5. powolne cofanie o jedną–dwie klatki;
6. ponowne wejście do sekcji;
7. test po zimnym ładowaniu i po cache.

Raportuj przebieg podczas ruchu i stan po 0,5–1 s ustalenia. FPS zmierzony
kilka sekund po zakończeniu animacji nie opisuje płynności samego filmu.

### 4. Macierz objaw → prawdopodobna przyczyna

| Objaw | Najczęstsza przyczyna | Sprawdź / rozwiązanie |
|---|---|---|
| Strona ma 60 FPS, film tnie | dekoder pomija klatki, playback rate za wysoki | `renderedFrame`, `skippedFrames`; zmniejsz tempo, użyj presented frame |
| Film długo dogania scroll | duży target drift, smoothing/lag albo zbyt niski rate | `maxTargetDriftMs`, preset, tempo wheel; duży skok domknij jednym seekiem |
| Film cofa się o klatkę | stary seek kończy się po nowszym celu lub overshoot interpolatora | jeden pending target, monotonic clamp, brak równoległych kontrolerów |
| Przy przewijaniu w górę WebM rusza od wcześniejszego miejsca do przodu | kierunek wyznaczono z `target-presented`, choć target właśnie się cofnął | porównaj target z poprzednim targetem i obsłuż cofanie przed `delta > 0` |
| Cofanie WebM tnie bardziej | długi GOP albo koszt dekodowania VP9 | sprawdź najpierw poprawność kierunku kontrolera; potem częstsze keyframe’y/GOP=1 lub WebP |
| Smugi między klatkami | canvas nie zastępuje poprzedniej bitmapy | `globalCompositeOperation='copy'`, brak crossfade, poprawna alfa |
| Czarny/pusty ekran | błędny asset/manifest/MIME, alpha mismatch, 404 | Network, `readyState`, `error`, `hasAlpha`, poster i ścieżka źródła |
| Pierwsze wejście tnie, kolejne nie | brak preloadu, zimny dekoder/cache, start w trakcie gestu | prewarm; WebM alpha i lokalny podgląd używają Blob, duży WebM bez alfy w produkcji może użyć natywnego URL |
| Tnie tylko WebM z alfą | VP9 alpha w Chromium trafia do ciężkiej ścieżki software | testuj `rVFC` i `getVideoPlaybackQuality()`; dla ścisłego scrubu użyj sekwencji WebP |
| Tnie przy 1080p, 720p działa | budżet dekodera/GPU/pamięci | profil jakości, DPR, liczba pikseli, hardware decode |
| Wrota nie reagują po cytacie | zewnętrzny przebieg ominął scheduler lub root jest zwinięty | użyj `setProgress`, inicjalizuj przed portalem, nie zapisuj bezpośrednio `currentTime` |
| Scroll jest oporny | Lenis/custom scroll ma za mały lerp lub zbyt długie doganianie | diagnozuj scroll osobno; nie kompensuj tego easingiem filmu |
| Jakość/kolor różnią się od źródła | ponowne kodowanie, JPEG, profil koloru, spłaszczenie alfy | passthrough WebM, WebP zamiast JPEG, kontrola manifestu i próbek |

### 5. Dobór formatu do zachowania

| Wymaganie | Preferowany wariant |
|---|---|
| Losowy scrub i częste cofanie bez alfy | MP4 H.264 z GOP=1 |
| Alfa, najwyższa kontrola klatki i cofanie | Klatki WebP |
| Alfa i zachowanie gotowego pliku bez konwersji | WebM passthrough, ale sprawdź GOP i wydajność VP9 alpha |
| Długi film, głównie ruch do przodu | natywny film z hybrydą play/seek |
| Czarna kompozycja, alfa nie jest faktycznie potrzebna | MP4 GOP=1 może być płynniejszy od VP9 alpha |
| Koniecznie każda klatka 60 FPS na monitorze 60 Hz | nie przyspieszaj filmu ponad 1×; dopasuj długość runwayu i tempo scrolla |

Nie da się jednocześnie zaprezentować każdej klatki źródła 60 FPS, przesunąć
materiał szybciej niż 1× i zachować 60 Hz monitora. To ograniczenie czasowe,
nie błąd JavaScript. Przy szybszym ruchu trzeba wybrać: pominięcie części
klatek, lag, seek albo dłuższy/slower scroll.

### 6. Reguły rozszerzania

- Nową scenę podłącz do istniejącego `CentralScheduler`.
- Jeśli postęp pochodzi z innej sekcji, użyj publicznego `setProgress`.
- Nie dodawaj drugiego listenera scroll ustawiającego `video.currentTime`.
- Nie uruchamiaj `requestAnimationFrame` per komponent.
- Utrzymuj jeden target, jeden aktywny seek i bounded cache.
- Dodaj nowe pole do schematu, modelu, Liquid, runtime, diagnostyki i testów;
  sama kontrolka panelu nie jest implementacją.
- Każdy nowy manifest musi opisywać rzeczywiste FPS, klatki, alfę i GOP.
- Zachowaj cleanup: pause, abort, observer disconnect, URL revoke i bitmap close.
- Sprawdź Shopify hot reload i MutationObserver, aby nie powstały dwie instancje.
- Przy zmianie algorytmu zachowaj zgodność MP4, WebM i WebP oraz reduced motion.
- Nie potwierdzaj 60 FPS ani alfy bez pomiaru klatek/obrazu i metadanych.

## Zasady wydajności i jakości

- Animuj `transform` i `opacity`; unikaj layoutu w każdej klatce.
- Nie trzymaj jednocześnie kontrolera MP4 i WebP w jednej instancji.
- Nie ustawiaj `currentTime` ani nie dekoduj obrazu bez zmiany celu.
- Dla MP4 scrollowanego używaj częstych keyframe’ów; referencja ma GOP=1.
- Dla gotowego WebM dłuższy GOP jest obsługiwany hybrydowo, ale GOP=1 nadal
  daje najlepsze cofanie i losowy scrub. Tryb hybrydowy nie zmienia pliku,
  jakości ani kanału alfa.
- Nie używaj JPEG dla sekwencji z alfą ani przy wymaganej zgodności kolorów.
- Poster pozostaje widoczny do gotowości pierwszej klatki.
- Błąd źródła pokazuje poster/fallback, nie pustą sekcję i nie blokuje scrolla.
- Podmiana zasobów tworzy rotacyjny backup; zachowywane są trzy ostatnie.

## Rozszerzanie systemu

Proste elementy DOM opisuj przez `data-scroll-animate`. Bardziej złożone
rejestruj przez `window.GicleeScrollFrameCanvas.registerElement(...)`.
Kontrakt polecenia, architektura, procedura diagnostyczna i Definition of done
znajdują się wyłącznie w tym dokumencie. Plik
`Film-scroll-AI-Integration-Guide.md` jest tylko historycznym odsyłaczem, aby
stare linki nie przestały działać.
