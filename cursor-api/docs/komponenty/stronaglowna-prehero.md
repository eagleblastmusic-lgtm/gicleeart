# Strona główna — Pre-Hero scroll media

## Pozycja w edytorze

Pierwsza strefa na liście komponentu **Strona główna**:

```text
Pre-Hero — scrollowane wideo
Hero — slideshow
Giclée Art — intro
…
```

Pre-Hero nie jest osobną natywną sekcją Shopify w `templates/index.json`. Front wstawia ją przed istniejące Hero przez zestaw assetów `giclee-home-prehero-*` oraz `giclee-home-hero-horizontal-curtain.*`.

## Pola edytora

- **Sekcja aktywna** — włącza lub usuwa pre-Hero z generowanego snippetu bez kasowania assetów.
- **Film do scrollowania** — upload lub wybór z Shopify Files; puste pole zachowuje lokalny `assets/giclee-home-prehero-scrub.mp4`.
- **Długość całej sekwencji (ekrany)** — np. `6` = `600vh`.
- **Start portalu przed końcem filmu (ekrany)** — np. `2` = portal zaczyna się około `200vh` przed końcem scrubbingu.
- **Wjazd oryginalnego Hero (ekrany)** — np. `1` = `100vh`.
- **Pokaż tekst w portalu**.
- **Tekst przejścia** — każda niepusta linia jest animowana osobno, maksymalnie pięć linii.
- **Pozioma kurtyna Hero → Giclée Art** — włącza drugie przejście po wycentrowaniu kolażu.
- **Postój wycentrowanego Hero (ekrany)** — domyślnie `1`, czyli `100vh` spokojnego scrolla bez ruchu filmu.
- **Otwieranie poziomej kurtyny (ekrany)** — domyślnie `1`, czyli pełne rozdzielenie górnej i dolnej części filmu podczas `100vh`.

Ustawienia trafiają do `config/settings_data.json`, więc są przechowywane osobno wraz z każdym wariantem strony głównej.

## Tryby scrolla

Selektor GicleeApp przechowuje tryb osobno dla każdego wariantu:

- **Zwykły — natywny** — bez dodatkowej bezwładności; punkt odniesienia wydajności.
- **Zwykły v2 — filmowy** — wygładza faktyczny ruch wywołany kółkiem myszy, zachowując natywny wygląd i geometrię strony.
- **Lenis — płynny** — eksperymentalny pełny smooth scroll; nie jest domyślną ścieżką produkcyjną.

### Zwykły v2 — filmowy

`assets/giclee-home-native-v2.js`:

- przechwytuje pionowe zdarzenie `wheel` wyłącznie na desktopie i rejestruje listener jako `passive: false`;
- zatrzymuje natychmiastowy skok tylko dla obsługiwanego kółka przez `preventDefault()`;
- kumuluje impulsy kółka w docelowej pozycji dokumentu;
- prowadzi rzeczywisty `window.scrollTo()` jednym krótkim RAF-em z lekkim wygaszeniem;
- nie używa Lenisa, nie przesuwa `body` i nie transformuje warstw strony;
- pozostawia natywne sterowanie dla klawiatury, paska przewijania, touch/coarse, gestów powiększania i przewijanych paneli zagnieżdżonych;
- omija elementy oznaczone `data-giclee-wheel-native` lub `data-lenis-prevent`, dialogi, drawery, modale, iframe i formularze wymagające natywnej obsługi;
- od razu synchronizuje się z ręcznym przeciągnięciem paska, klawiaturą, pointerdown, zmianą rozmiaru i pageshow;
- wyłącza się dla reduced motion, urządzeń touch/coarse, Shopify design mode i parametru `?giclee_native_scroll=1`.

Profil początkowy:

```text
wheelGain: 1
followTauMs: 105
maxWheelDeltaPx: 420
maxTargetLeadPx: 1200
```

Diagnostyka:

```js
window.GICLEE_NATIVE_V2_STATUS()
window.GICLEE_SMOOTH_SCROLL_STATUS()
window.GICLEE_FRAME_MONITOR(8000)
```

## Tryby renderowania scrubu

### Lenis — WebP na Canvas

Dla aktywnego Lenisa preferowana jest wygenerowana sekwencja WebP:

- domyślnie `20 FPS`, czyli około `100` klatek dla filmu pięciosekundowego;
- płaskie nazwy `assets/giclee-prehero-frame-0001.webp` itd.;
- wybór klatki z `scrollProgress × (frameCount - 1)`;
- rysowanie przez jeden `<canvas>` z kadrowaniem `cover`;
- ładowanie tylko aktualnej klatki i niewielkiego okna sąsiednich klatek;
- ograniczony cache dekodowanych obrazów zamiast trzymania całej sekwencji w pamięci;
- brak ładowania i brak `video.currentTime` dla MP4, gdy manifest WebP jest aktywny.

Generator:

```powershell
python scripts/build_prehero_webp_sequence.py
```

Tworzy klatki oraz aktualizuje:

```text
snippets/giclee-home-prehero-frame-manifest.liquid
```

Domyślny limit całej sekwencji wynosi `24 MB`. Można zmniejszyć rozdzielczość, jakość lub FPS parametrami `--width`, `--quality` i `--fps`.

### Scroll natywny i natywny v2 — MP4

Oba tryby natywne zachowują `assets/giclee-home-prehero-scrub.mp4`. Zwykły v2 zmienia wyłącznie oś czasu ruchu dokumentu uruchamianą przez kółko myszy; warstwy wizualne i mechanizm przewijania filmu pozostają takie jak w zwykłym trybie natywnym.

## Sekwencja

1. Natywne menu wyjeżdża do góry, a dolny czarny pas w dół.
2. Materiał pre-Hero jest sterowany pozycją scrolla.
3. W końcowej części filmu portal otwiera się symetrycznie od środka i pokazuje skonfigurowany tekst.
4. Po zakończeniu portalu od dołu wjeżdża oryginalny Hero Shopify z filmem-kolażem.
5. Hero pozostaje wycentrowany przez skonfigurowany pusty odcinek scrolla.
6. Pozioma szczelina dzieli ten sam działający film na część górną i dolną; otwarcie rozszerza się ku krawędziom.
7. Pod kurtyną jest wizualna kopia prawdziwej sekcji `Giclée Art — intro`; po pełnym otwarciu następuje bezszwowy hand-off do oryginalnej sekcji Shopify.

## Eksport

`Komponenty/stronaglowna/prehero_integration.py`, `prehero_full_generator.py` i `home_scroll_mode.py`:

1. rejestrują edytowalną strefę przed Hero,
2. odczytują i zapisują wartości oraz tryb scrolla wariantu,
3. owijają `write_home_assets()`,
4. eksportują `window.GICLEE_PREHERO_CONFIG`,
5. wybierają URL filmu z Shopify Files albo lokalny asset awaryjny,
6. zachowują manifest WebP, renderer Canvas i runtime Native v2,
7. zabezpieczają `snippets/giclee-home-stack-critical.liquid` przed utratą integracji po zapisie lub wdrożeniu,
8. ładują assety pionowego portalu i poziomej kurtyny.

Integracja jest dodawana tylko dla wariantu używającego `home_stack` i gdy lokalny snapshot motywu zawiera wymagane pliki kodu oraz dostępne źródło filmu.
