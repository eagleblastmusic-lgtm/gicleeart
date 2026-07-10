# Strona główna (landing)

Szablon: `templates/index.json` · GicleeApp: [`cursor-api/docs/komponenty/stronaglowna.md`](../../cursor-api/docs/komponenty/stronaglowna.md)

---

## Układ

Strona główna to sekwencja sekcji Horizon (slideshow, `section`, `divider`, bloki `comparison-slider`) — bez dedykowanego `giclee-homepage.liquid`.

| Kolejność | Sekcja | Typ treści |
|-----------|--------|------------|
| 1 | Slideshow full frame | Hero — 1 slajd |
| 2 | Giclée Art | Portret + opis pracowni |
| 3 | Odrestaurowywanie dzieł | Tekst + suwak przed/po |
| 4 | Autorska korekcja | Suwak + tekst + CTA |
| 5 | Potencjał… | Tekst + suwak |
| 6 | Zobacz różnicę | 2× suwak + tekst centralny |

Separatory: bloki `divider` między sekcjami (osobne sekcje Shopify) — **po jednym aktywnym** przed każdą kartą stacka (`--scroll`); wyłączone duplikaty usunięte z `templates/index.json`. Dodatkowo `divider_tjPVmp` po ostatniej karcie (przed stopką).

**Section-scroll (homepage):** `assets/giclee-home-section-scroll.js` + `.css` — ładowane tylko dla `request.page_type == 'index'` (`layout/theme.liquid`). Jeden wyraźny gest kółka/trackpada = przejście do następnej / poprzedniej sekcji; targety z `GICLEE_HOME_SECTIONS` w kolejności hooków (`hero`→…→`see-difference`, fallback: `#MainContent > .shopify-section` w kolejności DOM, ≥160px, bez separatorów) — **bez sortowania po live `offsetTop`**. **Canonical dock** liczony raz przy init / `resize` / `load` / `shopify:section:load` / `giclee:home-stack-ready` (pomiar przy `scrollY=0`, potem cache) — podczas scrolla wheel **nie** przelicza sekcji ani docków. Cel animacji = zamrożony canonical dock z layoutu (`documentTop − stopOffset`, index 0 → 0) — w sticky stacku `getBoundingClientRect().top ≈ 0` dla wielu warstw naraz, więc viewport rect służy tylko do debugu (`liveDock` vs `canonicalDock` w `GICLEE_HOME_SECTION_SCROLL.debug()`). **Aktywna sekcja nawigacyjna** (`activeSectionIndexForNavigation`): wyłącznie `scrollY` + cache `canonicalDockCache` — ostatni index z `scrollY >= dock[i] − tolerance`; wheel / keyboard / `stepDown` / `goToSection` **nie** używają `elementsFromPoint`. **Wizualna** (`viewportSectionIndex`) — tylko debug (`visualIdx` vs `navIdx`). `debug()` — asserty: monotoniczny dock, stała kolejność ID vs init, `slideshow_4LMfx7` = index 0, progi scrollY 1795/2748/3701/4503. Scroll w górę: powyżej docku (`scrollY > dock + 2 px`) → snap do góry bieżącej gdy runway ≥ `MIN_ANIM_PX` (80 px); krótszy runway → od razu poprzednia sekcja (uniknięcie niewidocznego snapu ~32 px w stacku); na docku → poprzedni niższy pin. Przy overlap stacku (scroll już na pinie poprzedniej karty, np. potencjał przy `scrollY = dock` korekcji) `resolveScrollUpTargetY` cofa o `MIN_ANIM_PX` w runway — inaczej delta ≈ 0 i gest nic nie robi. **Canonical dock w stacku** (`dockPositionsStack`): pin sticky `top:0` (nie `stopOffset`); monotonicznie rosnące docki — gdy `documentTop(sekcji) − stackPinTop` ≤ poprzedni dock + 48 px, fallback `prevDock + stackRunwayStep()` (uniknięcie zduplikowanych pinów od 3. sekcji). Scroll w dół: na współdzielonym pinie plateau → następny wyższy dock (`resolveScrollDownTargetIndex`). Offset stopu: `headerOffset` auto=0 w stacku + `headerOffsetExtra` + `separatorOffset` ≈ 32px — separator/seam widoczny w kadrze. Animacja: rAF + `easeOut` z wykładnikiem zależnym od `motionDynamics` (0 = cubic/spokojny, 100 = quint/dynamiczny); skala czasu `durationScale` 1.2→0.7 mnoży `minDuration`–`maxDuration`. Anty-kolejka: podczas animacji gesty blokowane; okno ciszy 180 ms **tylko dla tego samego kierunku** — odwrócony gest przechodzi natychmiast; mikro-ruchy poniżej `wheelThreshold` nie robią nic. Klawiatura: PageDown/PageUp/strzałki/Space/Home/End. Nie przechwytuje: ctrl/alt/meta+wheel, splash, site notice, `dialog[open]`, menu headera, `pm-app-drawer-open`, drag na `.comparison-slider`, wewnętrzne kontenery przewijane, pola formularzy, strefa stopki (za ostatnią sekcją scroll natywny). Mobile/touch: `mobileMode` = `native` (domyślnie — moduł nieaktywny) / `soft` (dociąganie po zatrzymaniu) / `disabled`. `prefers-reduced-motion`: `instant` (skok bez animacji) lub `off`. Konfiguracja: `window.GICLEE_HOME_SCROLL_CONFIG` w `assets/giclee-home-sections.js` (generuje GicleeApp → Strona główna → **Animacja przewijania…**; per wariant `data/variants/<id>/scroll.json`). Presety premium w panelu wypełniają formularz (Galeria, Editorial kontemplacyjny, Kinowy, Dynamiczny premium, Miękki editorial); zapis = jawne wartości w `scroll.json`. Kill switch: `enabled: false` → pełny natywny scroll; brak configu = bezpieczne domyślne. Debug: `GICLEE_HOME_SECTION_SCROLL.debug()` (`positions`, `navIdx`, `visualIdx`, `duplicateDocks`, `targetUp`/`targetDown`/`targetDownScrollY`); polish: `headingSettle` — 12px osadzenie nagłówka po docku (`.giclee-snap-settle`). Theme Editor (`Shopify.designMode`) → moduł wyłączony.

**Scroll-over (home3, home4):** Warstwy kart **2–5**: `min-height: 100svh` (runway sticky); **warstwa 6** — `min-height: auto` (bez pustego czarnego scrolla przed stopką). **Hero (warstwa 1):** pierwsza scena = jeden viewport (`header H + film + dolny czarny pas H`); film pozostaje full-width (`object-fit: cover`), wysokość strefy mediów `100svh - 2H` (clipping **tylko** na `.giclee-video-collage`; stage/video wypełniają host przez `inset: 0`). `--home-stack-hero-min-height` (inline na sekcji hero, `calc(100svh - heroTopPx)` z pomiaru `getBoundingClientRect().top`; nie na `<html>`) + `--home-stack-hero-header-height` / `--home-stack-hero-footer-height` / `--home-stack-hero-media-offset-top` ustawiane w JS (`applyHeroLayoutMetrics`) z pomiaru `#header-component.getBoundingClientRect().height` (init, 2×rAF, resize, `giclee:splash-done`). Dolny pas: `.giclee-home-hero-footer` (DOM, idempotentny) — czarne tło, wys. = header. Szewrony (`.giclee-home-scroll-cue`) w pasie, wyśrodkowane flexem; zanikają przez `--home-stack-under-dim`, ukryte do `giclee-home-stack-ready`. Sekcja 2 (Giclée Art) zaczyna się dopiero poniżej pierwszego viewportu (separator złoty + sticky stack bez zmian). **`nextTop` w viewport** (`boardTop` od `vh` → `PREV_PIN_EPS`, smoothstep) — fazy `approach` / `overlap` / `dock`. Przy najezdzie kolejnej karty sekcja pod spodem dostaje `--home-stack-under-dim` (blur + fade, min. opacity **28%** desktop / **50%** mobile) na `.background-image-container`, `video-background-component` i `.section-content-wrapper` — **nie** na `> .section-background` (czarna baza zostaje opaque → fade do czarnego). Warstwy tła sekcji: **czarne** `> .section-background` → wgrana grafika/film (`.custom-section-background`) → treść. Poślizg `--home-stack-slip-y` — ten sam offset na `> .section-background` + `> .section` karty **i** separatora `--scroll` (12% vh desktop); czarna kurtyna `::after` na wrapperze `shopify-section` (wys. = `--home-stack-slip-y`) zakrywa lukę nad przesuniętymi dziećmi. Seam/separator `--scroll`: `#000`. Pipeline motion: `targetProgress` → lerp `current` (rise `0.055` / decay `0.12`) → **easeInOutCubic**. Separatory `--scroll`: para **1→2** — `scaleX(1)` od startu; pozostałe — ten sam progress co karta. RAF aktywny przez cały gest scrolla. Debug: `GICLEE_HOME_STACK_DEBUG()` → `pairProgressInstant`, `phase`; `GICLEE_HOME_STACK_SLIP_CHECK()`. `prefers-reduced-motion` → bez smoothingu i poślizgu.

---

## Zachowanie poza Theme Editor

| Element | Plik |
|---------|------|
| Splash + scroll reveal | `layout/theme.liquid` |
| Mobile hero (lista z JS, nie hardcode) | `assets/giclee-home-mobile.js`, `layout/theme.liquid` |
| Hero kolaż wideo | `blocks/_slide.liquid`, `assets/giclee-hero-video-collage*.js`, `collage_gui.py` |
| **Opcjonalny ambient hero** | `sections/slideshow.liquid` (schema), `assets/giclee-hero-audio.js/.css` — tylko `index`, po kliknięciu; edycja w GicleeApp → **Strona główna** → Hero → **Dźwięk ambient…** |
| Hooki sekcji `data-giclee-home` | `assets/giclee-home-sections.js`, `giclee-home-sections-boot.js` |
| **Scroll-over warstw (home3, home4)** | `assets/giclee-home-stack.css`, `giclee-home-stack.js` — flaga `GICLEE_HOME_STACK` |
| **Pre-stack FOUC (home3, home4)** | `snippets/giclee-home-stack-critical.liquid` |
| **Section-scroll (jeden gest = sekcja)** | `assets/giclee-home-section-scroll.js/.css` — konfiguracja `GICLEE_HOME_SCROLL_CONFIG` |
| Animacja intro sekcji Giclée Art | `assets/giclee-home-studio-reveal.css`, `giclee-home-sections-boot.js` — reveal, gradient BIO, parallax; config `GICLEE_HOME_STUDIO_REVEAL_CONFIG` (GicleeApp → **Efekty…**); globalny scroll-reveal wyłączony w `assets/custom.css` |
| Efekty pozostałych sekcji (reveal, hover, tło) | `giclee-home-sections-boot.js` — `GICLEE_HOME_SECTION_EFFECTS_CONFIG` + `GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG` per hook (`restoration`, `color-correction`, `potential`, …) |
| Układ mobile sekcji | `assets/custom.css` |
| Suwaki przed/po | `blocks/comparison-slider.liquid`, `assets/comparison-slider.js` |
| **Przyciemnienie tła sekcji** | `snippets/section.liquid` (`.giclee-section-bg-overlay`), `assets/custom.css` — ten sam gradient co BIO; siła: `background_overlay_pct` (GicleeApp → **Tło…**) |
| **Hover/focus «Zobacz różnicę» (final)** | `assets/giclee-home-final-difference.css`, `giclee-home-sections-boot.js` — parametry z GicleeApp (**Animacja…**); opcja `reverseBehavior` odwraca trigger (hover na grafikach) |
| Modal «site notice» | `snippets/giclee-site-notice.liquid`, `?giclee_skip_notice=1` |

Parametry podglądu dev: `?giclee_skip_splash=1` (pomiń splash), `?giclee_skip_notice=1` (pomiń modal).

---

## Edycja treści

**GicleeApp → Strona główna** — sekcje, miniaturki, drag-and-drop, diff przed zapisem, walidacja, historia kopii, podgląd live/theme dev, deploy z wyborem celu.

Alternatywa: Shopify Theme Editor (ryzyko nadpisania przy deploy z repo).

Po zmianie w repo: **wdrożenie motywu** na sklep.
