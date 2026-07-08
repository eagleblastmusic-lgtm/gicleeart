# Scroll choreography — pusty scroll (wzór uniwersalny)

**Uniwersalna instrukcja** do sekwencji scroll-over: warstwy sticky, wjazd elementu, faza „pustego scrolla”, doczepienie treści pod spodem i powrót do zwykłego przewijania.

**Referencja w projekcie:** PDP v3 (`product.szablon-produktu-v3`) — sekcja na końcu dokumentu.

Powiązane: [`szablony-i-strony.md`](szablony-i-strony.md) · [`produkt-i-zoom.md`](produkt-i-zoom.md) · [`zaleznosci.md`](../zaleznosci.md).

---

## Kiedy stosować ten wzorzec

Użyj go, gdy na jednej stronie chcesz:

1. **Warstwowy scroll-over** — kolejne bloki „jadą” nad wcześniejszymi (sticky + z-index).
2. **Animowany wjazd** elementu (np. z boku), sterowany scrollowaniem użytkownika — nie autoplay.
3. **Pauzę po wjeździe** — użytkownik przewija, ale główny element zostaje na miejscu („pusty scroll”).
4. **Płynne przejście** do treści pod spodem — bez skoku, prześwitu i nagłego pojawienia się końca strony.

Typowe scenariusze: landing z hero + panel produktu, storytelling PDP, portfolio z nakładającymi się sekcjami, „scrollytelling” w motywie Shopify.

**Nie stosuj**, gdy wystarczy zwykły `position: sticky` bez choreografii albo gdy wystarczy CSS `scroll-snap` na prostym układzie kolumn.

---

## Słownik (terminologia ogólna)

| Termin | Znaczenie |
|--------|-----------|
| **Warstwa tła (backdrop)** | Element sticky pod spodem (np. zoom, zdjęcie) — zostaje, gdy wyższe warstwy jadą nad nim |
| **Warstwa sceny (stage)** | Blok sticky, na którym odbywa się akcja (np. opis) |
| **Element wjeżdżający (slider)** | Komponent wjeżdżający w trakcie scrolla (np. galeria + konfigurator) |
| **pinWrap** | Opakowanie DOM elementu wjeżdżającego — od niego mierzysz `pinTop` / `pinBottom` |
| **slotSpacer** | Niewidoczny placeholder na wysokość slidera, gdy ma `position: fixed` |
| **holdTail** | Niewidoczny spacer **stałej** wysokości — tu „zużywa się” pusty scroll |
| **Follower** | Treść **pod** pinWrap w HTML (np. sekcja „Jak powstaje…”) — dojeżdża do dolnej krawędzi slidera w fazie hold |
| **Zadokowanie (docked)** | Slider na miejscu (`pinTop <= 0`), trwa hold lub wspólny scroll z followerem |
| **Tryb normalny** | Koniec sekwencji — wszystkie warstwy w zwykłym flow dokumentu |

---

## Architektura DOM (szablon)

```
[warstwa sceny — sticky top:0]
[pinWrap]
  [slotSpacer]          ← height = wysokość slidera, tylko gdy slider jest fixed
  [slider]              ← element wjeżdżający (sticky w CSS; w fazie wjazdu: fixed)
  [holdTail]            ← height = HOLD_PX (stałe!), ustawione raz przy init
  [followerOverlap]     ← height = viewport (stałe przy init/resize) — scroll na overlay procesu nad sliderem
[follower A]            ← treść pod sliderem w dokumencie
[follower B]
...
```

**Zasada kolejności:** follower **musi** być w HTML **po** pinWrap. Wtedy w fazie hold scroll „zjada” holdTail, a follower naturalnie dojeżdża do dolnej krawędzi slidera — **bez** sticky-dock na followerze.

**Zasada tła:** kontener nadrzędny (shell) z pełnoszerokościowym tłem i `z-index` wyższym niż warstwa tła — szczeliny między blokami nie prześwitują.

---

## Fazy sekwencji (maszyna stanów)

Pętla `update()` na `scroll` + `resize` (+ `ResizeObserver` na kluczowe elementy):

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PRZED — scena jeszcze nie przyklejona (stage.top > 0)    │
│    → slider ukryty / poza sceną, brak hold                  │
├─────────────────────────────────────────────────────────────┤
│ 2. WJAZD — pinTop > 0                                       │
│    → slider position:fixed; top:0                            │
│    → animacja tylko na jednej osi (np. translateX)           │
│    → slotSpacer = wysokość slidera                           │
├─────────────────────────────────────────────────────────────┤
│ 3. ZADOKOWANY + HOLD — pinTop <= 0 AND pinBottom > 0        │
│    → slider sticky (fixed odpinany przy pinTop === 0)        │
│    → holdTail aktywny (stała wysokość)                       │
│    → zwolnij sticky warstwy pod spodem (żeby nie prześwitywały)│
├─────────────────────────────────────────────────────────────┤
│ 4. NORMALNY — pinBottom <= 0                                │
│    → sticky zdjęte, zwykły scroll strony                     │
└─────────────────────────────────────────────────────────────┘
```

**Postęp wjazdu** (gdy pinTop > 0):

```javascript
var t = smoothstep(1 - clamp(pinTop / rangeHeight, 0, 1));
// rangeHeight = wysokość warstwy sceny lub inny znany zakres scrolla
```

**Próg odpinania fixed → sticky:** `pinTop <= 0` (nie „prawie 1” postępu animacji). Wcześniejsze odpiecie = skok pionowy.

---

## Recepta — jak zbudować pusty scroll

### Krok 1: Stały holdTail

```javascript
var HOLD_PX = 240; // dobierz pod UX; typowo 1/4–1/3 viewportu
holdTail.style.height = HOLD_PX + 'px'; // RAZ przy init
```

- Scroll użytkownika „zjada” ten spacer — wizualnie slider stoi.
- **Nigdy** nie zwijaj `holdTail` w `update()` przy przejściach fixed→sticky.
- **Nie używaj** `window.scrollTo` / `scrollBy` do kompensacji — walka z momentum trackpada i migotanie.

### Krok 2: Hybrid fixed → sticky (wjazd bez skosu, odpięcie z histerezą)

| Faza | Pozycjonowanie slidera | Ruch |
|------|------------------------|------|
| Wjazd (`pinTop > 0`) | `position: fixed; top: 0` | Tylko jedna oś (np. `translateX`) |
| Histereza (`0 ≥ pinTop > -REFIX_PX`) | nadal `fixed; top: 0` | Brak (wizualnie == sticky) |
| Głębiej w holdzie | `position: sticky; top: 0` (w CSS) | Brak |

`slotSpacer.height = slider.offsetHeight` **tylko** gdy fixed; po odpieciu `0`.

**Dlaczego histereza, a nie flip dokładnie przy `pinTop = 0`:** kompozytor przewija o klatkę przed rAF-em. Przy scrollu **w górę** przez próg slider ze zdjętym fixed jest jeszcze sticky — a sticky przy `pinTop > 0` **zjeżdża z pinWrap w dół** (odbicie planszy + prześwit sceny na ułamek sekundy, tym większy, im szybszy scroll). W strefie histerezy fixed `top:0` i sticky `top:0` renderują się identycznie, więc spóźniona klasa niczego nie przesuwa — flip przy `-REFIX_PX` jest bezszwowy w obie strony. Warunek: `REFIX_PX < HOLD_PX` (sticky musi przejąć, zanim koniec pinWrap zacznie wypychać slider). U nas `REFIX_PX = min(HOLD_PX - 40, 200)`.

### Krok 3: Szerokość bez `100vw`

Przy full-bleed i przejściu fixed→sticky:

```javascript
var cw = document.documentElement.clientWidth;
el.style.setProperty('--slide-w', cw + 'px');
el.style.setProperty('--slide-ml', -padLeft + 'px');
```

`100vw` ≠ `clientWidth` przy pasku przewijania → poziomy skok (~ szerokość scrollbara).

### Krok 3b (opcja): warstwa sceny bottom-anchored

Domyślnie scena pinuje się `top: 0` (górna krawędź do góry ekranu). Gdy scena jest **niższa niż viewport** i ma zostać widoczna w całości (nie chować się pod nagłówek), przypnij ją **dolną krawędzią** do dołu ekranu:

```javascript
var stickyTop = Math.max(0, viewportH - stageHeight); // 0 gdy scena wyższa niż viewport
stage.style.setProperty('--stage-top', stickyTop + 'px');
```
```css
.stage-layer { position: sticky; top: var(--stage-top, 0px); }
```

**Uwaga 1:** bramka fazy wjazdu slidera nie może już zakładać `stageRect.top === 0`. Zmień warunek „scena przypięta” na `stageRect.top <= stickyTop + 1`.

**Uwaga 2 (pułapka tła):** jeśli shell ma pełnoekranowe czarne tło (`::before`) przywiązane do przewijającego się shellu, przy scenie bottom-anchored tło **wjedzie górą nad scenę** i zakryje pasek backdropu (u nas R2).

**Antywzorzec 1:** licz górną krawędź tła per klatka w JS (`stageRect.top - shellTop` na scroll przez rAF). Zmienna zawsze spóźnia się o jedną klatkę za kompozytorem sticky → krawędź tła **trzęsie się** przy scrollu.

**Antywzorzec 2 (dwa tryby absolute/fixed przełączane klasą):** tło shellu absolute od statycznej pozycji sceny, po przypięciu sceny klasa przełącza je na fixed od `stickyTop`. Wygląda bezszwowo przy wolnym scrollu, ale **kompozytor przewija sticky o klatkę (lub więcej) przed rAF-em JS** — przy szybkim scrollu absolute tło zdąży wjechać nad przypiętą scenę zanim klasa się przełączy → czarny pas nad sceną na ułamek sekundy, tym wyższy, im szybszy scroll.

**Wzorzec — kurtyna doczepiona do sceny (zero klas, zero lagów):** tło rysuje pseudo-element **samej sceny**, od jej górnej krawędzi w dół:

```css
.stage-layer::after {
  content: '';
  position: absolute;
  z-index: -2; /* pod treścią sceny, nad backdropem (z-index sceny > backdropu) */
  top: 0;
  left: 50%;
  width: 100vw;
  height: var(--curtain-h, 100vh); /* wysokość reszty shellu, z layoutu */
  transform: translateX(-50%);
  background: var(--tlo);
  pointer-events: none;
}
```

```javascript
// raz na layout/resize (wartości layoutowe, nie scrollowe):
shell.style.setProperty('--curtain-h', (shell.offsetHeight - stage.offsetTop) + 'px');
```

Kurtyna jedzie ze sticky sceną **na kompozytorze**, więc z definicji nigdy nie wystaje nad jej górną krawędź (pasek backdropu zawsze czysty) i bez opóźnienia kryje wszystko pod spodem (hold, szczeliny separatorów). Po docku scena (zwolniona do `relative`) jest przewinięta nad viewport — kurtyna kryje wtedy cały ekran, w tym pas nad dawnym `stickyTop` (dawna „Uwaga 4" rozwiązuje się sama). Osobne tło shellu staje się zbędne. Wysokość kurtyny liczona z layoutu; gdy scena jest sticky-przesunięta, kurtyna sięga poniżej końca shellu, ale ten obszar jest wtedy wiele viewportów pod ekranem.

**Uwaga 3 (pasek pod sliderem):** gdy slider (fixed, wjazd) jest niższy niż viewport, pod nim widać przypiętą scenę — a po docku nagle czarne tło (flip). Spójność daje „kurtyna slidera”: `slider.is-slide-fixed::after { top: 100%; height: 100vh; background: tło; }` — czarne przedłużenie wjeżdża razem ze sliderem, a po docku płynnie przejmuje je kurtyna sceny (ten sam kolor).

### Krok 4: Zwolnij sticky warstw pod spodem po zadokowaniu

Gdy slider zadokowany, warstwy sceny **pod** nim nie powinny zostać `sticky` — w szczelinach (hold, separatory) prześwitują tło.

```css
.shell.is-docked .stage-layer {
  position: relative;
}
```

### Krok 5: Follower — sticky „karta na karcie” (nie sticky-dock)

**Antywzorzec:** `position: sticky` na followerze z `top: wysokość slidera` (sticky-dock).

Przy odjeżdżaniu slidera w górę powstaje luka → follower „stoi” → skok na końcu sekwencji.

**Wzorzec (PDP v3):** follower `position: sticky; top: 0` z rosnącym `z-index` (proces 35 > grid 25; trust 40 > proces 35). **Grid → proces:** pusty spacer `giclee-grid-follower-overlap` (wys. viewport) w `pinWrap` po `holdTail` — daje scroll na overlay bez ujemnego marginu na wrapie. **Proces → trust:** stały `margin-top: calc(-100dvh - gap)` na `.giclee-trust` + `min-height: 100dvh` na obu sekcjach. Wspólne tło graficzne: jeden obraz na `.pdp-v3-pt-wrap::before` z `background-attachment: fixed` (bez per-sekcji duplikatów). Po `is-scroll-normal` sticky zdjęte.

### Krok 6: Tło i z-index

- Shell z `z-index` > warstwa tła.
- Tło pod szczelinami = **kurtyna doczepiona do sceny** (patrz Krok 3b), nie osobne `::before` shellu przełączane klasami.
- `overflow-y: auto` **nie** na sticky warstwach wewnątrz sekwencji — pułapka scrolla (kółko nie przewija strony).

### Krok 7: Dostępność

```javascript
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  // slider od razu na miejscu, bez animacji wjazdu
  return;
}
```

---

## Szablon kodu (minimalny)

```javascript
function initScrollChoreography({ pinWrap, slider, stage, shell, holdTail, slotSpacer, HOLD_PX }) {
  holdTail.style.height = HOLD_PX + 'px';

  var REFIX_PX = Math.min(HOLD_PX - 40, 200);
  var isFixed = false;

  function setFixed(on) {
    if (on === isFixed) return;
    isFixed = on;
    slotSpacer.style.height = on ? slider.offsetHeight + 'px' : '0px';
    slider.classList.toggle('is-slide-fixed', on);
  }

  function setDocked(on) {
    shell.classList.toggle('is-docked', on);
  }

  function update() {
    var stageRect = stage.getBoundingClientRect();
    var pinTop = pinWrap.getBoundingClientRect().top;
    var pinBottom = pinWrap.getBoundingClientRect().bottom;

    if (stageRect.top > 0) {
      setFixed(false);
      setDocked(false);
      return;
    }

    if (pinBottom <= 0) {
      setFixed(false);
      setDocked(true);
      shell.classList.add('is-scroll-normal');
      return;
    }

    shell.classList.remove('is-scroll-normal');

    if (pinTop > 0) {
      setDocked(false);
      setFixed(true);
      // ustaw postęp wjazdu (translateX, opacity, …)
      return;
    }

    if (pinTop > -REFIX_PX) {
      // histereza: nadal fixed top:0 (== sticky) — bez odbicia przy scrollu w górę
      setDocked(true);
      setFixed(true);
      return;
    }

    setFixed(false);
    setDocked(true);
    // slider na miejscu, holdTail pracuje
  }

  window.addEventListener('scroll', function () {
    requestAnimationFrame(update);
  }, { passive: true });
}
```

---

## Antywzorce (uniwersalne)

| Objaw | Typowa przyczyna | Naprawa |
|-------|------------------|---------|
| Skok w dół + skos po wjeździe | Odpiecie fixed za wcześnie + `100vw` | `pinTop <= 0`; `clientWidth` zamiast `vw` |
| Lekki ruch do góry po skoku | Sticky przejmuje z opóźnieniem | Synchronizacja fixed/sticky na tym samym progu |
| Prześwit warstwy pod spodem | Sticky sceny nie zwolnione po dock | Klasa `is-docked` → `position: relative` |
| Follower stoi, potem skok | Sticky-dock followera | Follower w flow pod pinWrap |
| Nagły skok treści po hold | `holdTail` zwijany w runtime | Stała wysokość holdTail od init |
| Migotanie / szarpnięcie | `scrollTo` / `scrollBy` | Tylko spacer DOM + natywny scroll |
| Pułapka scrolla | `overflow-y: auto` na warstwie | `overflow: hidden` lub brak wewnętrznego scrolla |
| Skokowy scroll na warstwie interaktywnej | Ręczny `scrollBy` na wheel | Passthrough do natywnego scrolla strony |
| Magnetic snap + choreografia | Dwa systemy na jednym scrollu | Osobna decyzja UX; łatwo o konflikt |
| Krawędź tła trzęsie się przy scrollu | Zmienna CSS liczona per klatka w rAF goni sticky (lag 1 klatki) | Kurtyna doczepiona do sceny (pseudo-element sticky sceny); zmienne tylko przy layout/resize |
| Czarny pas nad sceną przy szybkim scrollu | Tło shellu absolute→fixed przełączane klasą; kompozytor wyprzedza rAF | Kurtyna doczepiona do sceny — jedzie ze sticky na kompozytorze, bez klas |
| Follower niewidoczny pod kurtyną sceny | Kurtyna `story::after` wystaje poza box; scena ma z-index 20, follower bez z-index | Followerom nadane z-index z mapy warstw (`--pdp-v3-process-z` itd.) > scena |
| Follower niewidoczny mimo z-index na dziecku | Wrapper followerów (`isolation: isolate`) bez własnego z-index — dziecko 35 w kontekście wrapu na auto/0, scena 20 wygrywa | `z-index` na wrapperze (np. `.pdp-v3-pt-wrap`) ≥ `--pdp-v3-process-z` |
| Follower nie zakrywa sticky slidera | Follower wchodzi dopiero gdy `pinWrap` się kończy i slider traci sticky (min-height 100dvh) | Spacer `giclee-grid-follower-overlap` (1× viewport) w `pinWrap` po `holdTail` |
| Tło proces+trust „resetuje się” między sekcjami | Osobny `background-image` na `::before` każdej sekcji (`center`) | Jeden obraz na `.pdp-v3-pt-wrap::before` + `background-attachment: fixed` |
| Kurtyna sceny zakrywa viewport po docku | `curtain-h` liczone od opisu; opis (relative) odjeżdża w górę, kurtyna zostaje w viewport | Wyłączyć kurtynę przy `.is-grid-docked` / `.is-scroll-normal` |
| Slider „odbija w dół” przy scrollu w górę z docku | Flip fixed→sticky dokładnie przy `pinTop = 0`; spóźniony sticky zjeżdża z pinWrap | Histereza: fixed trzymany do `pinTop = -REFIX_PX` (tam oba stany renderują się tak samo) |
| Jasny pasek na krawędzi tła z nakładką | Obraz na osobnej warstwie kompozytora (filter/will-change) rastruje się o px szerzej niż nakładka | Nakładka z zapasem (`inset: -4px`), kontener z `overflow: hidden` przycina |
| Nieprzyciemniony prześwit grafiki na krawędziach sekcji | Grafika `scale(1.03)`, nakładka bez scale — obraz wystaje poza nią | Ten sam `transform` na nakładce co na grafice |
| Znikająca 1px krawędź ramki przycisku na transformowanym gridzie | Ramka rysowana pseudo-elementem na `inset: 0` pod `overflow: clip` — raster na ułamkowych pozycjach obcina linię | Prawdziwy `border` na elemencie (część boxa, nie podlega clipowi) |

---

## Checklist — nowa implementacja

**DOM i kolejność**

- [ ] pinWrap owija slider + holdTail
- [ ] Follower(y) **po** pinWrap w HTML
- [ ] Shell z tłem pod szczelinami

**Logika**

- [ ] holdTail ustawiony raz, stała wysokość
- [ ] Odpiecie fixed przy `pinTop <= 0`
- [ ] slotSpacer tylko w fazie fixed
- [ ] `is-docked` zwalnia sticky warstw pod spodem
- [ ] Brak `scrollTo` w pętli scroll

**CSS**

- [ ] Szerokość z `clientWidth`, nie `100vw`
- [ ] Wjazd na jednej osi (bez skosu pionowego w fixed)
- [ ] `prefers-reduced-motion` obsłużone

**Weryfikacja w DevTools**

- [ ] `pinBottom > 0` przez ~`HOLD_PX` px po wjeździe
- [ ] Brak skoku `getBoundingClientRect().top` slidera przy odpieciu
- [ ] Follower dojeżdża do dolnej krawędzi slidera przed wspólnym odjazdem

---

## Decyzje do podjęcia w nowym projekcie

| Pytanie | Wskazówka |
|---------|-----------|
| Ile px hold? | 200–400 px lub ~25–35% viewportu; test na mobile |
| Co mierzyć jako `rangeHeight`? | Wysokość warstwy sceny albo dedykowany spacer nad pinWrap |
| Fixed czy tylko sticky? | Fixed na wjazd poziomy; sticky na hold — hybrid najstabilniejszy |
| Czy follower ma być sticky kiedykolwiek? | Raczej nie — tylko flow |
| Osobny wheel handler? | Tylko gdy warstwa przechwytuje scroll (zoom, mapa) — osobny moduł |

---

## Referencja: PDP v3 (GicleeArt)

Implementacja wzorca na szablonie `product.szablon-produktu-v3`.

### Mapowanie terminów

| Ogólne | PDP v3 |
|--------|--------|
| Warstwa tła | R2 (`.giclee-product-zoom`, sticky, z-index 12) |
| Warstwa sceny | `.giclee-product-story` (z-index 20, **bottom-anchored**: `top` = `--pdp-v3-story-top` = `max(0, vh − storyH)`; pasek R2 widoczny nad opisem) |
| Kurtyna tła | `.giclee-product-story::after` (wysokość `--pdp-v3-curtain-h` = shell − offset opisu, z JS przy layout/resize) |
| Slider | `.product-information__grid` (galeria + konfigurator, z-index 25) |
| pinWrap | `.giclee-grid-slide-pin` |
| Follower | `.giclee-process`, potem `.giclee-trust` — oba `sticky; top: 0` z rosnącym z-index (35 / 40), zakrywają poprzednią warstwę przy scrollu |
| Shell | `.product-information` (z-index 14; bez własnego tła — kryje kurtyna opisu) |

### Kolejność w `product-information-content.liquid`

1. `.giclee-product-story`
2. `.giclee-grid-slide-pin` → grid
3. `.giclee-before-after-target`
4. `.giclee-process`
5. `.giclee-trust`

### Kod i assety

| Plik | Rola |
|------|------|
| `assets/giclee-product-story.js` | `initGridSlide()` |
| `assets/giclee-product-story.css` | sticky, z-index, klasy stanów |
| `snippets/product-information-content.liquid` | kolejność sekcji |
| `sections/product-information.liquid` | `?v=` cache bust |

### Klasy stanów (PDP v3)

| Klasa | Faza |
|-------|------|
| `.is-grid-slide-fixed` | Wjazd (fixed) + strefa histerezy w holdzie |
| `.is-grid-slide-active` | Slider w scenie |
| `.is-grid-slide-done` | Wjazd zakończony |
| `.is-grid-docked` | Zadokowany + hold |
| `.is-scroll-normal` | Koniec choreografii |

### Zmienne CSS (PDP v3)

`--pdp-v3-grid-slide-x`, `--pdp-v3-grid-w`, `--pdp-v3-grid-ml`, `--pdp-v3-grid-pad-left/right`, `--pdp-v3-story-top`, `--pdp-v3-curtain-h`

### Wersja referencyjna

Stabilny stan: `story-20260702-curtain-hysteresis` (2026-07-02).

### Historia skrócona (PDP v3)

1. Wjazd grida z prawej na sticky opisie.
2. `scrollTo` / `scrollBy` — odrzucone.
3. `holdTail` — działa przy stałej wysokości.
4. Sticky-dock procesu (`top: wysokość slidera`) — odrzucony (luka + skok).
5. `is-grid-docked` + follower w flow; od 2026-07-08: `sticky top:0` na followerach (karta na karcie nad gridem / procesem).
6. Tło shellu absolute/fixed (`is-story-pinned`) — odrzucone (czarny pas nad opisem przy szybkim scrollu; kompozytor wyprzedza rAF). Zastąpione kurtyną `story::after`.
7. Flip fixed→sticky przy `pinTop=0` — zastąpiony histerezą (`REFIX_PX`), bo przy scrollu w górę grid odbijał w dół.

### Poprawki artefaktów renderowania (2026-07-02)

- **Config-bg (konfigurator):** nakładki `__overlay`/`__gradient` z `inset: -4px` — obraz na własnej warstwie kompozytora rastrował się o px szerzej niż nakładka (jasny pasek z lewej).
- **Tło proces+trust (`.pdp-v3-pt-wrap`):** `::after` (przyciemnienie) dostaje ten sam `scale(1.03)` co grafika w `::before` — bez tego obraz wystawał górą i dołem nieprzyciemniony.
- **Niedostępne warianty:** w v3 przywrócona prawdziwa ramka (`border-width`) zamiast pseudo-ramki motywu na `inset: 0` pod `overflow: clip` — na transformowanym gridzie górna 1px linia znikała przy ułamkowych pozycjach rastra (pseudo-ramki `::before`/`::after` → `border-color: transparent`).

---

## Powiązane problemy w tym projekcie (osobne moduły)

- **Zoom R2 a scroll strony:** [`produkt-i-zoom.md`](produkt-i-zoom.md) — wheel passthrough, nie mieszać z choreografią grida.
- **Stronicowany opis:** metafield `story_pages`, GicleeApp `stronaproduktu` — [`zaleznosci.md`](../zaleznosci.md).
