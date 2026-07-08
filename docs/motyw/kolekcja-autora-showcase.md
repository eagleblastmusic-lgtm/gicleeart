# Kolekcja autora — interaktywna galeria

Hub motywu: [`README.md`](README.md)

Sekcja premium do prezentacji dzieł z kolekcji Shopify — styl muzealny, ciemne tło, złamane akcenty. Dwa układy w ustawieniach sekcji.

---

## Pliki

| Plik | Rola |
|------|------|
| `sections/giclee-artist-collection-showcase.liquid` | Sekcja + schema Theme Editor |
| `snippets/giclee-artist-showcase-build-handle-list.liquid` | Kolejność autorów z menu (do 3 poziomów) lub fallback `collections` |
| `snippets/giclee-artist-showcase-artist-json.liquid` | Jeden wpis JSON autora (produkty, preview) |
| `assets/giclee-artist-collection-showcase.css` | Styl coverflow + editorial + panel scroll + nawigacja autorów |
| `assets/giclee-artist-collection-showcase.js` | Oryginał referencyjny (backup — nie ładowany bezpośrednio na stronie) |
| `assets/giclee-karuzela.js` | **Karuzela** — router wersji (localStorage + `?giclee_karuzela=`) |
| `assets/giclee-karuzela1.js` | **Karuzela1** — oryginalna karuzela bez dynamicznego tła |
| `assets/giclee-karuzela2.js` | **Karuzela2** — karuzela + tło obrazu aktywnego produktu |
| `assets/giclee-karuzela2.css` | Style warstw tła Karuzela2 |
| `sections/giclee-artist-biography.liquid` | Sekcja biograficzna autora (u góry strony kolekcji) |
| `assets/giclee-active-author.js` | Wspólny stan `activeAuthor` (bio + galeria + URL + SEO) |
| `assets/giclee-artist-biography.js` / `.css` | Synchronizacja biografii z nawigacją galerii |
| `assets/giclee-bio-collection-scroll-stack.css` | Scroll-overlap BIO → kolekcja (`position: sticky` + z-index; bez scroll JS / spacerów) |

**Stack:** motyw Shopify (Liquid + vanilla JS). Nie React — dopasowane do `pusty/`.

---

## Karuzela — zachowanie (Karuzela1 / Karuzela2) i wygląd sekcji (V1 / V2)

Sekcja ładuje `assets/giclee-karuzela.js`, który wybiera implementację JS **oraz** ustawia `data-giclee-showcase-look="V1|V2|V3"` na `<html>` (tylko tło sekcji karuzeli, bez wpływu na BIO).

| Wersja JS | Plik | Opis |
|--------|------|------|
| **Karuzela1** (domyślna) | `giclee-karuzela1.js` | Oryginał — ciemne tło gradient, bez obrazu produktu w tle |
| **Karuzela2** | `giclee-karuzela2.js` + `giclee-karuzela2.css` | Cinematic hero — tło = obraz aktywnego slajdu (crossfade ~780 ms), overlay + gradient + vignette; **scroll-stack:** tło z blur → ostrość (`--gacs-progress`); **zmiana autora** używa tego samego crossfade (bez resetu warstw), preload pierwszego slajdu w fazie wyjścia |

| Wygląd | CSS | Opis |
|--------|-----|------|
| **V2** (domyślny) | tokeny w `giclee-artist-collection-showcase.css` | Jaśniejsze tło sekcji z większą teksturą |
| **V3** | `[data-giclee-showcase-look="V3"]` | Spokojniejsze tło — mniej kontrastu/nasycenia, karuzela dominuje |
| **V1** | `[data-giclee-showcase-look="V1"]` + override w `giclee-karuzela2.css` | Ciemniejsze tło jak przed korektą balansu światła |

**Persystencja Karuzela1/2:**
1. parametr URL `?giclee_karuzela=Karuzela1|Karuzela2` (zapisuje też do localStorage),
2. `localStorage` klucz `giclee-carousel-version`,
3. `assets/giclee-carousel-config.js` → `__GICLEE_CAROUSEL_DEFAULT` (GicleeApp → Zapisz),
4. fallback: Karuzela1.

**Persystencja wyglądu V1/V2/V3:**
1. URL `?giclee_showcase_look=V1|V2|V3` (+ localStorage `giclee-showcase-look`),
2. `__GICLEE_SHOWCASE_LOOK_DEFAULT` w `giclee-carousel-config.js`,
3. fallback: V2.

**GicleeApp:** kafelek **Karuzela** — osobne radio dla zachowania i wyglądu sekcji (V3 = uspokojone tło). **Zapisz** → `settings.json` + config motywu (wymaga deploy).

**API w przeglądarce:** `GicleeKaruzela.setVersion('Karuzela2')`, `GicleeKaruzela.setShowcaseLook('V3')` — przeładowuje stronę.

Źródło obrazu tła: ten sam produkt co karta slajdu — atrybut `data-image-base`. Shopify CDN z limitem **max 3840×2160 px**, `crop=center`, `format=webp`, wymiary dopasowane do viewportu × DPR (min. 1280×720). Karta karuzeli nadal ~900 px, `sizes` desktop **28vw**.

---

## Nawigacja między autorami

**Domyślnie (auto):** sekcja buduje listę z podmenu **Katalog** (do 3 poziomów flyoutu) i **dołącza pozostałe kolekcje** sklepu — kolejność menu, potem reszta alfabetycznie z `collections`. Pomija ukrytych autorów: konfiguracja w **GicleeApp → Submenu katalog** (`assets/giclee-catalog-submenu-config.json`) oraz `gacs_hidden_csv` w tej sekcji (nawigacja prev/next) — **obie listy trzymaj zsynchronizowane**. Nie filtruje po `products_count` w pętli `for nav_col in collections` (w Shopify bywa niedostępne w tej pętli).

Przyciski **← Poprzedni autor** / **Następny autor →** są na wysokości nagłówka „Wybrane dzieła” (nie przy karuzeli). Hover pokazuje miniaturę kolejnej/poprzedniej kolekcji. Przejście: blur + translate3d + opacity, easing `cubic-bezier(0.22, 1, 0.36, 1)`, bez przeładowania strony (`history.pushState`).

Ustawienia sekcji:
- **Źródło listy autorów:** `Automatycznie z menu Katalog` (domyślnie) lub `Ręczne bloki`
- **Menu nawigacji:** zwykle `main-menu`
- **Pozycja menu z autorami:** domyślnie `Katalog`

Ręczne bloki (opcjonalnie): Theme Editor → **Dodaj blok** → **Autor / kolekcja** — nadpisują auto, gdy źródło = ręczne bloki.

Na stronie kolekcji startowy autor = bieżący `collection.handle`. Klik **Poprzedni / Następny autor** — animacja bez przeładowania; URL przez `history.pushState`.

### Synchronizacja całej strony (`activeAuthor`)

Jeden stan `GicleeActiveAuthor` (`assets/giclee-active-author.js`) kontroluje:

- sekcję **Biografia autora** (`giclee-artist-biography`) — zdjęcie, nazwisko, lata życia, opis, cytat z `collection.description`;
- sekcję **Kolekcja autora — galeria** — karuzela i nawigacja autorów;
- **URL** (`history.pushState` / `popstate`) i **SEO** (`document.title`, `meta description`, `canonical`, Open Graph).

Dane biograficzne każdego autora są w JSON galerii (`bioHtml`, `bioBackgroundUrl`, `bioBackgroundPosX`, `seoTitle`, `seoDescription` w `giclee-artist-showcase-artist-json.liquid`).

**Tło BIO per kolekcja (GicleeApp → Tło do Bio):** metafield kolekcji `custom.bio_background_url` (URL z Shopify Files) + opcjonalnie `custom.bio_background_pos_x` (0–100, przesunięcie poziome kadru), `custom.bio_background_overlay_pct`, `custom.bio_background_cover_scale`, `custom.bio_background_radial_mask` (JSON: maska radialna ekspozycji obok gradientu pod tekst), `custom.bio_background_menu_gradient` (`none` \| `narrow` \| `wide` \| `wide_bottom` \| `wide_v2` \| `wide_v3` \| `wide_v3_bottom` — gradient u góry hero do czerni pod menu; domyślnie `wide` gdy brak metafield; `wide_bottom` jak szeroki + ten sam pas u dołu; `wide_v2` bez płaskiego pasu #000 u góry; `wide_v3` jak v2, wysokość pasu 60%; `wide_v3_bottom` jak v3 + dół). SSR w `giclee-artist-biography.liquid`; przy przełączaniu autorów `giclee-artist-biography.js` → `applyBackground()` ustawia `object-position`, parametry overlay i klasę `giclee-artist-biography-section--menu-gradient-wide` lub `--menu-gradient-narrow`. Warstwy: obraz (`cover`) + asymetryczny overlay (`.giclee-artist-bio-bg__overlay`) + opcjonalna maska radialna (`.giclee-artist-bio-bg__radial-mask`) + opcjonalnie u góry gradient do `#000` (`.custom-section-background::before`, wysokość od `--header-group-height`) pod czarne menu. Przy `--custom-bg` ukrywany jest `.section-background` (scheme motywu), żeby nie prześwitywał jasna obwódka przy pierwszym załadowaniu. **Fallback:** brak metafield → tło z Theme Editor. Admin: [`tldobio.md`](../../cursor-api/docs/komponenty/tldobio.md).

**Linki do produktów po zmianie handle:** JSON w HTML może mieć stare `product.url` (cache strony). `GicleeArtistExhibition` przy starcie i przy przełączeniu autora pobiera świeże produkty z `GET /collections/{handle}/products.json` i buduje URL z `handle`. Przy zmianie handle w Admin API (`update_product` w `shopify_client.py`) tworzony jest redirect `/products/{stary}` → `/products/{nowy}`; backfill: `cursor-api/scripts/backfill_product_handle_redirects.py`.

**Animacje biografii:** tło — crossfade w fazie wyjścia (0.88s); **tekst i portret** — zsynchronizowane z nagłówkiem karuzeli (`giclee:artist-showcase-enter` w `swapAndEnter`, ta sama animacja wejścia 0.88s). **Scroll-shift (editorial):** od pierwszego piksela scrollu nazwa + portret w lewo, akapity opisu w prawo — progress `scrollY / (wysokość strony − viewport)` z ease-in (`t^1.4`); rozmycie + fade-out (`opacity` → 0) zsynchronizowane z przesunięciem; **tło** — zoom stacku + fade-out całej warstwy tła (`--gab-scroll-bg-stack-scale`, `--gab-scroll-shift-opacity` na `[data-gab-custom-bg]`); desktop max ~160px, tablet ~96px, mobile wyłączone. `prefers-reduced-motion` wyłącza też crossfade i przejścia tekstu.

**Stabilność layoutu przy zmianie autora:** overlay-audit (grid, tło `inset:0`); stała wysokość **`.giclee-artist-bio`** w CSS (`--gab-hero-height: clamp(560px, 56svh, 640px)` — pas bio na desktopie; mobile v49: `height:auto`). **Scroll-overlap BIO → galeria:** `assets/giclee-bio-collection-scroll-stack.css` — BIO `sticky` (`z-index: 20`), galeria `relative` (`z-index: 30`), header obniżony do `10`; ładowane gdy włączone **Panel scroll** w sekcji galerii (`enable_scroll_panel`, domyślnie tak). Galeria bez fade-in przy scrollu (pełna widoczność nagłówka, stage, kropek).

**Skrypty stanu** (`giclee-active-author.js`, `giclee-artist-biography.js`) ładują się z sekcji galerii; `giclee-artist-biography.js` ładuje się też z sekcji biografii (scroll-shift na stronach bez galerii). Cache-bust: `&v=` / `?v=` na assetach biography.

**Biografia (Collection heading / Biografia autora):** `giclee-artist-biography.js` subskrybuje `GicleeActiveAuthor`. Boot biografii **po** `GicleeActiveAuthor.init()` w galerii.

**Nakładka tła biografii:** jeden asymetryczny overlay (`.giclee-artist-bio-bg__overlay` — lewa ciemniejsza pod tekst, środek/prawa odsłania kolaż; winieta w tej samej warstwie) **oraz** opcjonalna maska radialna ekspozycji (`.giclee-artist-bio-bg__radial-mask`, osobna warstwa nad gradientem). Przy metafield collage — theme overlay wyłączony. Fallback Theme Editor — ten sam gradient na `.overlay--solid`. Mobile: mocniejszy overlay. Portret: delikatna korekta `filter/box-shadow` w CSS. Treść `z-index: 2+`.

**Mobile galeria (≤749px):** mniejsze slajdy coverflow (`--gacs-slide-w/h`), padding `__inner` z `--page-margin`, nagłówek pełna szerokość, nawigacja autorów prev|next w jednym wierszu pod nagłówkiem, karuzela: viewport pełna szerokość + strzałki w drugim rzędzie stage. Na urządzeniach dotykowych autoplay karuzeli jest wyłączony, żeby slajd nie przestawiał się sam podczas oglądania; swipe działa także po rozpoczęciu gestu na linkowanej karcie.

**Warstwa tekstowa (overlay):** absolutnie pozycjonowane napisy — lewy dół: data / technika / gatunek aktywnego slajdu; prawy dół: cytat z listy `custom.collection_quotes`. **Fade-in na końcu scrollu strony:** meta (gdy `scrollY` ≥ ~90% zakresu dokumentu i galeria w viewportcie) → po ~1.05 s cytat (`is-gacs-end-slide-*` w overlay JS).

---

## Wpięcie w motyw

1. **Theme Editor** → strona kolekcji autora (lub dowolna strona).
2. **Dodaj sekcję** → **„Kolekcja autora — galeria”**.
3. Ustaw **Kolekcję** (lub zostaw pustą na stronie kolekcji — użyje bieżącej `collection`).
4. Wybierz układ:
   - **3D coverflow (wow)** — karuzela orbit, aktywna karta na środku, tilt przy hover.
   - **Editorial** — asymetryczna siatka muzealna, ten sam modal szczegółów.

Opcjonalnie: ukryj standardową siatkę `main-collection` w edytorze, jeśli galeria ma zastąpić grid produktów. **Uwaga:** na szablonie `collection.json` siatka jest wyłączona — pełna lista dzieł musi mieścić się w ustawieniu **Liczba dzieł** sekcji galerii (max 50 bez paginacji Shopify).

---

## Ustawienia sekcji

| Ustawienie | Domyślnie |
|------------|-----------|
| Kolekcja | — (na PDP kolekcji: bieżąca) |
| Liczba dzieł | 50 (max Shopify bez paginacji; wcześniej 12 — karuzela nie pokazywała całej kolekcji) |
| Układ | coverflow |
| Etykieta / tytuł / opis / CTA | konfigurowalne |
| Autoplay | wł. co 7 s (tylko coverflow; pauza przy hover/focus) |
| Pokaż przycisk CTA | checkbox w sekcji (domyślnie wł.) |
| Wysuwany panel nad poprzednią sekcją | domyślnie wł.; galeria nachodzi na treść i header przy scrollu |

---

## Panel ekspozycyjny (scroll)

Efekt luksusowej warstwy — galeria wysuwa się nad poprzednią sekcję i przykrywa sticky header.

| Mechanizm | Opis |
|-----------|------|
| `position: sticky` + `transform: translate3d` | Płynny ruch powiązany ze scrollem (rAF, 60 FPS) |
| `--gacs-gap` | Odstęp od poprzedniej sekcji na starcie (przed nachodzeniem) |
| `--gacs-overlap` | Maks. wysunięcie panelu w górę podczas scrollu |
| `--gacs-layout-trim` | Kompensacja layoutu = `--gacs-overlap × progress`; `margin-bottom` na `.gacs-panel-scroll__sticky` + `syncPanelHeight()` w JS (border box panelu = dół showcase) |
| Sentinel + `.gacs-panel-scroll__surface` | Progress ze scrolla bez transform na sticky (brak jitteru) |
| `--layer-gacs-exhibition` (100000) | `.gacs-section-over-chrome` nad headerem; przy overlap `visibility:hidden` na `.header-section` |
| Scroll panel | `translate3d` na `__surface`; `__surface::before` (gradient u góry, **za** treścią); sekcja `z-index:100000` nad mega menu; obcinanie od dołu przez `syncPanelHeight()` |
| `pointer-events: none` (przed `.is-overlapping`) | Panel ma `padding-top` w flow nad bio — bez tego przechwytuje wheel/scroll w dolnej części biografii |
| Tło w `--gacs-gap` | Przezroczyste przed nachodzeniem (widać dół biografii); gradient na warstwach panelu |
| `.gacs-under-panel` | Klasa na poprzedniej `.shopify-section` (JS pomija `divider` między bio a galerią) — subtelne przyciemnienie |
| `prefers-reduced-motion` | Wyłącza efekt (statyczny układ) |

Wyłączenie: Theme Editor → sekcja → odznacz **„Wysuwany panel nad poprzednią sekcją”**.

**Galeria kończy stronę** (domyślnie wł.): wyłącza `flex-grow: 1` ostatniej sekcji (`base.css`), chowa stopkę, kompensuje layout po `translateY` — bez pustej przestrzeni pod galerią.

### Dlaczego wcześniej była czarna pustka

1. **`flex-grow: 1`** na `.content-for-layout > .shopify-section:last-child` — ostatnia sekcja (galeria) rozciągała się do wysokości viewportu; tło sekcji wypełniało resztę czarnym.
2. **`transform: translateY()`** na `.gacs-panel-scroll__surface` — przesuwa warstwę wizualnie w górę, ale **nie zmienia** wysokości w flow; bez kompensacji zostaje pusty pas o wysokości `--gacs-overlap × progress`.
3. **`body { min-height: 100svh }` + `main { flex: 1 }`** — przy krótszej treści main nadal rozciągał stronę.

Fix: `:has(.gacs-end-page)` / klasa JS → `flex-grow: 0`, kompensacja layoutu po `translateY`:

1. **`margin-bottom: calc(-1 * trim)`** na `.gacs-panel-scroll__sticky` (nie na `__surface` — transform nie skraca sticky).
2. **`syncPanelHeight()`** w JS — `height` na `.gacs-panel-scroll` (obcinanie od dołu); przy overlap `overflow: visible` na panelu i `.gacs-section-end-page.gacs-section-over-chrome` (góra nie jest clipowana przy `translateY`).
3. **`readCssLength()`** — odczyt `--gacs-overlap` z CSS (Safari/Chrome zwraca `clamp(...)` jako tekst; parseFloat dawał 120 zamiast ~162 px).

### Czarny pasek u góry viewportu (overlap, audyt Playwright 2026-06-05)

Trzy nakładające się przyczyny (nie jeden element):

1. **Sticky `.header-section`** (`z-index: 8`) — transparentne tło, ale rysowany nad galerią w pasie 0–`--header-group-height` → widać `body { background: #000 }`. Fix: `visibility: hidden` na headerze gdy `.gacs-panel-scroll.is-overlapping`.
2. **`overflow: hidden` na `.gacs-panel-scroll`** — obcinał `__surface` po `translateY` w górę. Fix: `overflow: visible` przy `.is-overlapping` / `.is-pinned-top` + w `syncPanelHeight()`.
3. **`overflow: hidden` na `.gacs-section-end-page`** — ten sam clip na poziomie `.shopify-section` (sekcja `top` > 0). Fix: `.gacs-section-end-page.gacs-section-over-chrome { overflow: visible }`.

**Cache:** `&gab=gacs-coverflow-overflow-v18-20260616` (CSS), `gacs-skip-redundant-fetch-v18-20260616` (JS).

### Jasny pasek / prześwit na szwie bio → galeria (2026-06-28)

Podczas overlapu widać cienką jasną linię nad nagłówkiem galerii (subpixel + zaokrąglenie + obrys):

1. **`box-shadow: 0 0 0 1px rgba(255,255,255,…)`** na `.gacs-panel-scroll__surface` — usunięty (hairline).
2. **`border-radius: 0` + `margin-top: -2px`** na `.giclee-artist-showcase` już przy `.is-overlapping` (wcześniej dopiero przy pin).
3. **`::before`** na `__surface` — 8px przedłużenie `--gacs-bg` w górę przy overlap/pin.
4. **JS `seamCover: 2px`** — dodatkowy `translateY` w `GicleeArtistScrollPanel.update()`.

**v68a (2026-07-01):** hover-blur zawężony — trigger tylko nad kartą **aktywnego** slajdu (`.giclee-artist-showcase__slide.is-active .giclee-artist-showcase__slide-card`, delegacja `pointerover/out`), nie cały viewport. Cache: `karuzela2-bg-hover-blur-v2-active-slide-20260701` / `karuzela-router-v15`.

**v68 (2026-07-01):** Karuzela2 — rozmycie tła po najechaniu na obraz karuzeli (blur 6px na `.giclee-karuzela2-bg`, klasa `is-gac-k2-hover-blur`); przełącznik w aplikacji Karuzela (`window.__GICLEE_HOVER_BLUR_ENABLED`, localStorage `giclee-karuzela-hover-blur`, URL `?giclee_hover_blur=on|off`, API `GicleeKaruzela.setHoverBlur`); wyłączone na touch/`prefers-reduced-motion`. Cache: `karuzela2-bg-hover-blur-20260701` / `karuzela2-css-hover-blur-20260701` / `karuzela-config-v2` / `karuzela-router-v14`.

**v67 (2026-07-01):** Karuzela2 — subtelny mouse parallax tła (warstwa `__layers`, overscan `scale(1.08)`, przesunięcie ±22px/±14px, lerp `pointermove`, recenter przy `pointerleave`/`blur`); wyłączony na touch i `prefers-reduced-motion`. Cache: `karuzela2-bg-parallax-20260701` / `karuzela2-css-bg-parallax-20260701`.

**v66 (2026-07-01):** Karuzela2 blur→ostrość — fix: progress z pozycji showcase w viewportcie (CSS scroll-stack bez `data-gacs-scroll-panel`); osobny listener scroll. Cache: `karuzela2-bg-blur-scroll-v2-20260701`.

**v65 (2026-07-01):** overlay — fix fade-out przy scrollu w górę (reguły `is-gacs-end-scroll-hide-armed` po `meta-in`/`quote-in`; rAF przed klasą hide). Cache: `gacs-overlay-v18-end-scroll-hide-fix-20260701`.

**v64 (2026-07-01):** Karuzela2 — tło slajdu startuje rozmyte (`blur` ~11px), nabiera ostrości wraz ze scroll-stackiem (`--gacs-progress`, ease `t^1.35`); mobile i `prefers-reduced-motion`: bez blur. Cache: `karuzela2-bg-blur-scroll-20260701` / `karuzela2-css-bg-blur-scroll-20260701`.

**v63 (2026-07-01):** overlay — fade-out meta + cytat przy scrollu w górę (animacja ~680 ms). Cache: `gacs-overlay-v17-end-scroll-out-20260701`.

**v62 (2026-07-01):** overlay — fade-in przy scrollu do końca strony

**v61 (2026-07-01):** overlay karuzeli — fade-in meta + cytat sekwencyjnie (trigger: ostatni slajd — cofnięte w v62)

**v60 (2026-07-01):** fix skoku zoomu tła przy 1. scrollu — baseline stacku `1.04` gdy włączone cover-scale (metafield). Cache: `gab-scroll-shift-v39-20260701`.

**v59 (2026-07-01):** scroll-shift — przywrócony zoom tła z fade-out (stack + cała warstwa). Cache: `gab-scroll-shift-v38-20260701`.

**v58 (2026-07-01):** scroll-shift — wyłączony zoom tła (zostaje fade-out). Cache: `gab-scroll-shift-v37-20260701`.

**v57 (2026-07-01):** fix zoom + fade-out tła — scale na `[data-gab-bg-stack]`, fade na `[data-gab-custom-bg]` (overlay nie maskuje zaniku). Cache: `gab-scroll-shift-v36-20260701`.

**v56 (2026-07-01):** scroll-shift — fade-out tła bio zsynchronizowany z zoomem (`--gab-scroll-shift-opacity` na grafice). Cache: `gab-scroll-shift-v35-20260701`.

**v55 (2026-07-01):** scroll-shift — zoom tła bio przy scrollu (`--gab-scroll-bg-scale`, zsynchronizowany z progress). Cache: `gab-scroll-shift-v34-20260701`.

**v54 (2026-07-01):** scroll-shift — przywrócony fade-out (`--gab-scroll-shift-opacity` → 0). Cache: `gab-scroll-shift-v33-20260701`.

**v53 (2026-07-01):** scroll-shift — wyłączony fade-out (`opacity` stałe 1); zostaje lewo/prawo + blur. Cache: `gab-scroll-shift-v32-20260701`.

**v52 (2026-07-01):** wyłączony fade-in galerii przy scrollu (nagłówek, stage, kropki — stała widoczność). Cache: `bio-scroll-stack-v7-20260701`, `gab-scroll-shift-v31-20260701`.

**v51c (2026-07-01):** fade-in galerii — opacity startuje od 0 (kalibracja `revealStart` przy górze strony; domyślne `0` w CSS). Cache: `gacs-scroll-fade-v6-20260701`, `gab-scroll-shift-v30-20260701`.

**v51b (2026-07-01):** fade-in galerii — także `__header-row` (Wybrane dzieła + prev/next autor). Cache: `gacs-scroll-fade-v5-20260701`, `gab-scroll-shift-v29-20260701`.

**v51a (2026-07-01):** fade-in galerii — fix: cel `__stage` + `__dots` (nie `__exhibition-content`), opacity od viewportu. Cache: `gacs-scroll-fade-v4-20260701`, `gab-scroll-shift-v28-20260701`.

**v51 (2026-07-01):** scroll-shift — fade-out (`--gab-scroll-shift-opacity` → 0) zsynchronizowany z lewo/prawo + blur. Cache: `gab-scroll-shift-v27-20260701`.

**v50z (2026-07-01):** fade-in galerii — fix widoczności: opacity od `scrollY` (0 na górze), `__exhibition-content` domyślnie ukryte. Cache: `gacs-scroll-fade-v3-20260701`, `gab-scroll-shift-v26-20260701`.

**v50y (2026-07-01):** scroll-shift — blur (`--gab-scroll-shift-blur`) zsynchronizowany z przesunięciem lewo/prawo. Cache: `gab-scroll-shift-v25-20260701`.

**v50x (2026-07-01):** fade-in galerii — fix: tylko `__stage` (nie cała sekcja), bez transition 0.88s podczas scrollu, nagłówek pełna widoczność. Cache: `gacs-scroll-fade-v2-20260701`, `gab-scroll-shift-v24-20260701`.

**v50w (2026-07-01):** scroll-shift — cofnięcie o krok: dystans ~160px / ~96px, krzywa `t^1.4` (bez mieszanki liniowej). Cache: `gab-scroll-shift-v23-20260701`.

**v50v (2026-07-01):** galeria / karuzela — fade-in przy scrollu (`--gacs-scroll-fade-opacity`, ease-out quad). Cache: `gacs-scroll-fade-v1-20260701`, `gab-scroll-shift-v22-20260701`.

**v50u (2026-07-01):** scroll-shift — cofnięcie dystansu do ~220px / ~128px (desktop / tablet). Cache: `gab-scroll-shift-v21-20260701`.

**v50t (2026-07-01):** scroll-shift — większy dystans końcowy (desktop ~280px, tablet ~160px). Cache: `gab-scroll-shift-v20-20260701`.

**v50s (2026-07-01):** scroll-shift — większy dystans końcowy (desktop ~220px, tablet ~128px)

**v50r (2026-07-01):** scroll-shift — jeszcze szybszy start (`0.38·t + 0.62·t^1.55`). Cache: `gab-scroll-shift-v18-20260701`.

**v50q (2026-07-01):** fade menu — jeszcze szybsze znikanie (~6% viewportu + tail ~28px, łącznie ~80px). Cache: `bio-header-fade-v8-20260701`, `gab-scroll-shift-v17-20260701`.

**v50p (2026-07-01):** scroll-shift — szybszy start ease-in (`t^1.4` zamiast `t²`). Cache: `gab-scroll-shift-v16-20260701`.

**v50o (2026-07-01):** fade menu — jeszcze szybsze pełne znikanie (~9% viewportu + krótszy tail). Cache: `bio-header-fade-v7-20260701`, `gab-scroll-shift-v15-20260701`.

**v50n (2026-07-01):** scroll-shift — ease-in (`progress²`), przyspieszenie przesunięcia wraz ze scrollem. Cache: `gab-scroll-shift-v14-20260701`.

**v50m (2026-07-01):** fade menu — szybsze pełne znikanie (krótszy tail ~0.95× wys. menu). Cache: `bio-header-fade-v6-20260701`, `gab-scroll-shift-v13-20260701`.

**v50l (2026-07-01):** fade menu — fix unoszenia przy scrollu (wyłączenie `scroll-up` idle Horizon, sticky `top:0`); szybszy fade (~14% viewportu, krzywa √). Cache: `bio-header-fade-v5-20260701`, `gab-scroll-shift-v12-20260701`.

**v50k (2026-07-01):** fade menu — fix: pełna widoczność na `scrollY=0`; ściemnienie ~90% dopiero po ~25% wys. bio / ~32% viewportu scrollu. Cache: `bio-header-fade-v4-20260701`, `gab-scroll-shift-v11-20260701`.

**v50j (2026-07-01):** fade menu — kalibracja do widoku bio + „Wybrane dzieła” u dołu: ~90% ściemnienia (`opacity≈0.1`) gdy góra kolekcji jest w pasie ~82% viewportu; dalszy scroll do zera. Cache: `bio-header-fade-v3-20260701`, `gab-scroll-shift-v10-20260701`.

**v50i (2026-07-01):** scroll-shift — jeszcze większy dystans (desktop max ~160px, tablet ~96px). Cache: `gab-scroll-shift-v9-20260701`.

**v50h (2026-07-01):** scroll-shift — większy dystans lewo/prawo (desktop max ~96px, tablet ~56px). Cache: `gab-scroll-shift-v8-20260701`.

**v50g (2026-07-01):** fix fade menu — cel `#header-component` (nie `#header-group` z `display:contents`), `--gab-header-fade-opacity`. Cache: `gab-scroll-shift-v7-20260701`, `bio-header-fade-v2-20260701`.

**v50f (2026-07-01):** scroll-shift — daty (`h4`) w lewo, portret (`img`) w prawo (zgodnie ze szablonem bio kolekcji). Cache: `gab-scroll-shift-v6-20260701`.

**v50e (2026-07-01):** fade-out menu (`#header-group`) na stronie kolekcji autora — opacity od 1. px scrollu (`scrollY / --header-group-height`), przywraca przy powrocie na górę. Cache: `gab-scroll-shift-v5-20260701`, `bio-header-fade-20260701`.

**v50d (2026-07-01):** scroll-shift — portret `data-gab-scroll=left` (nie na kontenerze body), overflow visible na treści (fix przycinania tytułu). Cache: `gab-scroll-shift-v4-20260701`.

**v50c (2026-07-01):** scroll-shift — start od 1. px scrollu (`scrollY / zakres strony`), tło statyczne, napisy lewo/prawo do końca dokumentu; portret jak tytuł (lewo), akapity osobno (prawo). Cache: `gab-scroll-shift-v3-20260701`.

**v50b (2026-07-01):** scroll-shift — fix zatrzymywania przy sticky BIO: progress od pin-scroll przez cały overlap z galerią (travel ~78% wysokości showcase), bez resetu IO przy sticky; transform bez transition 0.88s. Cache: `gab-scroll-shift-v2-20260701`.

**v50 (2026-07-01):** scroll-shift biografii — editorial drift przy scrollu (nazwa + tło/portret w lewo, opis w prawo); `data-gab-scroll` na title/body/bg; wyłączone na mobile ≤749px i przy `prefers-reduced-motion`. Cache: `gab-scroll-shift-20260701`.

**v49 (2026-07-01):** jasna obwódka przy własnym tle BIO (pierwsze załadowanie / upload) — inna przyczyna niż sam `.section-background`: (1) `scroll-stack` ustawiał `background-color: var(--color-background)` na `.custom-section-background`; (2) subpixel przy `sticky` + `translateZ(0)` na szwie góra/dół hero; (3) inline script szukał `.giclee-artist-biography-section` wewnątrz hosta (`querySelector` bez matcha na samym `#shopify-section`). Fix: `#000` przy `--custom-bg`, `inset box-shadow` na kontenerze tła (bez przesunięcia kadru `object-fit`), `visibility:hidden` na `[data-gab-custom-bg]` do `img.onload`, poprawiony inline script (`host` = sekcja).

**Cache:** `gab-seam-fix-20260701` (biography CSS/liquid), `bio-seam-fix-20260701` (scroll-stack CSS).

**v48 (2026-06-22):** szybkie kliknięcia w fazie wejścia — przekierowanie do wyjścia (`transitionPhase`, bez `clearStates`); kolejność klas enter przed remove exit; CSS anti-flash bio.

**v47 (2026-06-22):** `brightness()` w animacji autora — stan spoczynku `blur(0) brightness(1)`; wyjście 100%→88%, wejście 92%→100% (płynna interpolacja z blur); overlay `::after` tylko przy wyjściu (jak v45).

**v46 (2026-06-22):** blur przy fade autora przywrócony (`blur(7px)` / `blur(5px)`); bez `brightness()` — barwy karuzeli bez wypłukiwania; overlay `::after` nadal tylko w fazie wyjścia.

**v45 (2026-06-22):** animacja zmiany autora — usunięty `filter: brightness/blur` z `.exhibition-content` (barwy karuzeli od razu po wejściu); overlay `::after` tylko w fazie wyjścia; `is-artist-transitioning` zdejmowany na starcie fade-in.

**v44 (2026-06-22):** szybkie kliknięcia w trakcie animacji autora — `targetArtist` / `targetArtistIndex` kolejkowany bez gwałtownego `reconcile`; po zakończeniu fazy łańcuch kolejnej animacji wyjścia/wejścia (`transitionSeq`).

**v42 (2026-06-22):** `end_page` — usunięty +32px fudge w `syncPanelHeight` po pin; `trimEndPageScrollBleed()` (ujemny `margin-bottom` = nadmiar scrollHeight); coverflow `display:none` dla `|offset|>4`; viewport `contain` + `max-height`.

**v41 (2026-06-22):** porównanie z referencyjnym HTML (t/50, overlay-audit): `--gab-hero-height` na `.giclee-artist-bio` (nie na tle — grid rozciąga `custom-section-background`); przywrócony overlay-audit bez `position:absolute` na tle; `end_page` bez wymuszonego `--static` (jak referencja).

**v40 (2026-06-22):** stały pasek grafiki bio w CSS (`--gab-hero-height`, tło `position:absolute`); usunięty `.gacs-bio-collection-spacer` (nie było w referencyjnym HTML); przywrócony `padding-top: var(--gacs-gap)` na `end_page` static — jak w działającym układzie overlay-audit.

**v38 (2026-06-22):** przywrócony układ **overlay-audit** (grid `grid-row:1`, `{% render 'overlay' %}`, `vertical-alignment: center`, padding 48/48). `height:auto !important` + czyszczenie locków przy boot.

**v34 (2026-06-22):** bio — `height:auto` (override base `layout-panel-flex`), nakładka na zdjęciu tła (jak audit), bez locka layoutu na `end_page`, czyszczenie `gacs-layout-locked` po zmianie autora.

**v33 (cofnięte częściowo):** tylko `flex-start`; v34 domyka layout.

**v29 (2026-06-22):** panel statyczny (`end_page` / touch) — `update()` nie ustawia już `is-pinned-top` (po zmianie autora `refreshScrollPanels` zostawiał ukryty header bez listenera scroll).

**v28 (2026-06-22):** szybka nawigacja „Poprzedni/Następny autor” — `targetArtistIndex` + `reconcileArtistTarget()` (URL nie wyprzedza galerii); ignorowanie przeterminowanych `products.json` (`productFetchSeq`). To samo w `giclee-artist-biography.js` (`targetArtist`).

**v25 (2026-06-22, przywrócony):** coverflow — animacja wejścia/wyjścia karty na brzegu stosu (offset 4, parkowanie transform na `±4`, `visibility:hidden` dla `|offset|>4`). Scroll-panel na `end_page` (nie `.gacs-end-page-gap`). **Cofnięto v26/v27** — znany problem: czarna przestrzeń na dole przy dużych kolekcjach.

**v27 (cofnięte):** `end_page` — `.gacs-end-page-gap` zamiast scroll-panelu; `stabilizeEndPageLayout()`.

**v26 (cofnięte):** `display:none` dla `|offset|>4`; viewport/track `contain` + `max-height`; `trimEndPageScrollBleed()`.

**v24 (2026-06-22):** `end_page` static — przywrócony `padding-top: var(--gacs-gap)` (czarna przerwa między bio a galerią); bez scroll-linked trim u dołu.

**v23 (2026-06-22):** `end_page` — panel scroll w trybie statycznym (bez `syncPanelHeight` / ujemnego `margin-bottom` przy scrollu); showcase `end_page` zawsze `overflow-y: clip`. Naprawia „duchowy” scroll (pasek kurczy się, widok stoi).

**v22 (2026-06-22):** coverflow — slajdy z `|offset| > 3` dostają `display:none` zamiast ekstremalnych transform 3D (rozpychały `scrollHeight` przy pierwszych/ostatnich dziełach dużej kolekcji). Viewport: `overflow: clip`. `syncPanelHeight` mierzy od `.giclee-artist-showcase__inner`.

**v21 (2026-06-16):** karuzela bez ceny pod tytułem — tylko obraz + skrócony tytuł (wymiary paska tytułu bez zmian).

**v20 (2026-06-16):** skrót tytułu karuzeli obcina też `(lub …)` / ` (lub …)` — nie tylko gołe «A lub B».

**v19 (2026-06-16):** tytuł slajdu karuzeli = tylko wariant główny (ucięcie przed « lub » / « or » / « oder » …); snippet `giclee-showcase-slide-title.liquid` + `shortCarouselTitle()` w JS.

**PDP (2026-06-23):** ten sam snippet w `snippets/text.liquid` — bloki tekstowe z `{{ closest.product.title }}` w szablonach produktu (`templates/product*.json`) pokazują skrócony tytuł bez `(lub …)`; bloki `product-title` i sticky ATC już wcześniej.

**v18 (2026-06-16):** coverflow nie jest obcinany przed scroll-overlap (`overflow-x: visible` na showcase/stage/viewport). JS nie nadpisuje już gotowego HTML przy starcie — używa produktów z JSON Liquid (bez zbędnego `products.json`); fetch tylko gdy brak danych; cache per autor; `reinit()` ponawia layout po paint.

**Mobile v17:** naprawione kliknięcie w kafelek — warstwa `.giclee-artist-showcase__track` (3D coverflow) przechwytywała hit-test zamiast slajdów/linków; `pointer-events: none` na track + `auto` na slide, pominięcie drag przy `pointerdown` na linku, fallback `resolveLinkFromPoint()` + `location.assign()`.

Cache (legacy): `&gab=mobile-scroll-static-v17-20260606`.

**Regresja po pullu theme `199535001948`:** wariant nie miał wysokiego `--layer-gacs-exhibition` ani klasy `.gacs-section-over-chrome`. Po scrollu i kliknięciu **Następny autor** animacja galerii/bio odsłaniała sticky header albo clipping panelu, więc nad segmentem „Kolekcja autora” pojawiał się `body #000`. Fix v11: end-page ma `--gacs-overlap: 1px`, bo duży overlap (~162px) podnosił całą galerię i zostawiał pusty pas na dole viewportu. Runtime: przy max scroll `.giclee-artist-showcase` kończy się na ~899px dla viewportu 900px.

**Responsive v12:** dopasowanie tylko dla `max-width:1199px` i niżej. Desktop `>=1200px` bez zmian wymiarów coverflow (np. 1440px: aktywna karta 340×480). Breakpointy:
- laptop `990–1199px` — nieco mniejsze karty i ciaśniejsze odstępy;
- tablet `750–989px` — mniejsze karty, krótsze odstępy i ukryte preview autorów;
- telefon `<=749px` / `<=420px` — ciaśniejszy nagłówek, mniejsza karta, krótsze kropki/nawigacja, na bardzo wąskich ekranach ukryty lead.

**Mobile v13:** poprawiony gest karuzeli na telefonie. `pointerdown` nie odrzuca już startu na `.giclee-artist-showcase__slide-link`, `touch-action: pan-y` zostawia pionowy scroll strony, a poziomy drag przełącza slajd niższym progiem na dotyku. Autoplay nie startuje na urządzeniach dotykowych/coarse pointer, więc widok nie „resetuje się” sam przy oglądaniu. Przyciski autorów na telefonie są wymuszone przez `grid-template-areas` jako `prev | next` pod nagłówkiem i mają mniejszy typ oraz wysokość.

**Mobile v14:** poprawiony konflikt scroll vs swipe. Gest na karcie rozpoznaje teraz oś ruchu: pionowy ruch natychmiast puszcza karuzelę i nie wywołuje `preventDefault`, a poziomy swipe przełącza slajd dopiero po wyraźnym przekroczeniu progu. `setPointerCapture()` nie jest używany dla dotyku, żeby nie przejmować scrolla strony. Dodatkowo `#page-transition.opening` w `layout/theme.liquid` ma `pointer-events: none`, bo overlay otwierania potrafił zostać nad kolekcją i przechwytywać dotyk mimo niewidocznych paneli.

**Mobile v15:** panel ekspozycyjny (`data-gacs-scroll-panel`) jest statyczny na urządzeniach dotykowych/coarse pointer. `GicleeArtistScrollPanel` dodaje `.gacs-panel-scroll--static` i nie podpina scroll-linked `update()`, więc telefon nie zmienia dynamicznie wysokości/transformacji panelu podczas pionowego scrolla. Desktop zachowuje overlap/sticky efekt.

### Czarna pustka u dołu viewportu (overlap, audyt Playwright 2026-06-05)

`translateY(-overlap×progress)` na `__surface` podnosi showcase (`100svh`), ale **nie wydłuża** go wizualnie — dolna krawędź = `100svh − overlap×progress` (np. 162 px luki przy pełnym pinie). Sticky jest transparentny → widać `body #000`. Dokument kończy się poprawnie (`syncPanelHeight`, `gapBelowViewport: 0`), ale **w viewport** zostaje czarny pas.

Fix: `background: var(--gacs-bg-gradient)` na `.gacs-panel-scroll__sticky` przy overlap fullscreen — luka pod showcase (translateY vs 100svh) nie pokazuje już `body #000`; bez zmiany layoutu / scrollHeight.

**Cache:** `gicleeart.eu` może serwować stary HTML sekcji (Cloudflare) — po pushu odśwież cache lub sprawdź `?preview_theme_id=197314249052`.

---

## Interakcje

- **Coverflow:** strzałki, kropki, drag myszą, swipe (pointer), klawiatura (← → w viewport). **Klik w kartę → strona produktu** (`<a href>`).
- **Editorial:** klik w dzieło → strona produktu.
- **A11y:** `aria-label`, focus states, `prefers-reduced-motion` wyłącza autoplay i ciężkie animacje.

---

## Deploy

```powershell
cd c:\Strona\pusty
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live `
  --only "sections/giclee-artist-collection-showcase.liquid" `
  --only "snippets/giclee-artist-showcase-artist-json.liquid" `
  --only "snippets/giclee-artist-showcase-track.liquid" `
  --only "snippets/giclee-product-body-fact.liquid" `
  --only "assets/giclee-artist-collection-showcase.css" `
  --only "assets/giclee-karuzela.js" `
  --only "assets/giclee-karuzela1.js" `
  --only "assets/giclee-karuzela2.js" `
  --only "assets/giclee-karuzela2.css" `
  --only "assets/giclee-showcase-slide-overlays.css" `
  --only "assets/giclee-showcase-slide-overlays.js" `
  --only "assets/giclee-carousel-config.js" `
  --only "assets/giclee-active-author.js" `
  --only "assets/giclee-artist-biography.js" `
  --only "assets/giclee-artist-biography.css" `
  --only "assets/giclee-bio-collection-scroll-stack.css" `
  --only "sections/giclee-artist-biography.liquid" `
  --only "templates/collection.json"
```

Po zmianie JS/CSS bump `?v=` w sekcji liquid.

---

## Przykład konfiguracji (kolekcja Van Gogh)

- **Kolekcja:** handle artysty w Shopify
- **Nazwa artysty:** Vincent van Gogh
- **Układ:** coverflow na stronie głównej kolekcji; editorial na landingach redakcyjnych
- **CTA:** „Zobacz całą kolekcję” → URL kolekcji

Bez wybranej kolekcji w edytorze motywu sekcja pokazuje **6 placeholderów** (podgląd layoutu).
