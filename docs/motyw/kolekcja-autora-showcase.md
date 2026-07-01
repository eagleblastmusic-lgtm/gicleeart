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
| **Karuzela2** | `giclee-karuzela2.js` + `giclee-karuzela2.css` | Cinematic hero — tło = obraz aktywnego slajdu (crossfade ~780 ms), overlay + gradient + vignette; **zmiana autora** używa tego samego crossfade (bez resetu warstw), preload pierwszego slajdu w fazie wyjścia |

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

**Domyślnie (auto):** sekcja buduje listę z podmenu **Katalog** (do 3 poziomów flyoutu) i **dołącza pozostałe kolekcje** sklepu — kolejność menu, potem reszta alfabetycznie z `collections`. Pomija ukrytych autorów: `HIDDEN_CATALOG_ARTISTS` w `layout/theme.liquid` (panel Katalog + menu mobilne) oraz `gacs_hidden_csv` w tej sekcji (nawigacja prev/next) — **obie listy trzymaj zsynchronizowane**. Nie filtruje po `products_count` w pętli `for nav_col in collections` (w Shopify bywa niedostępne w tej pętli).

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

**Tło BIO per kolekcja (GicleeApp → Tło do Bio):** metafield kolekcji `custom.bio_background_url` (URL z Shopify Files) + opcjonalnie `custom.bio_background_pos_x` (0–100, przesunięcie poziome kadru), `custom.bio_background_overlay_pct`, `custom.bio_background_cover_scale`, `custom.bio_background_radial_mask` (JSON: maska radialna ekspozycji obok gradientu pod tekst), `custom.bio_background_menu_gradient` (`none` \| `narrow` \| `wide` — gradient u góry hero do czerni pod menu; domyślnie `wide` gdy brak metafield). SSR w `giclee-artist-biography.liquid`; przy przełączaniu autorów `giclee-artist-biography.js` → `applyBackground()` ustawia `object-position`, parametry overlay i klasę `giclee-artist-biography-section--menu-gradient-wide` lub `--menu-gradient-narrow`. Warstwy: obraz (`cover`) + asymetryczny overlay (`.giclee-artist-bio-bg__overlay`) + opcjonalna maska radialna (`.giclee-artist-bio-bg__radial-mask`) + opcjonalnie u góry gradient do `#000` (`.custom-section-background::before`, wysokość od `--header-group-height`) pod czarne menu. Przy `--custom-bg` ukrywany jest `.section-background` (scheme motywu), żeby nie prześwitywał jasna obwódka przy pierwszym załadowaniu. **Fallback:** brak metafield → tło z Theme Editor. Admin: [`tldobio.md`](../../cursor-api/docs/komponenty/tldobio.md).

**Linki do produktów po zmianie handle:** JSON w HTML może mieć stare `product.url` (cache strony). `GicleeArtistExhibition` przy starcie i przy przełączeniu autora pobiera świeże produkty z `GET /collections/{handle}/products.json` i buduje URL z `handle`. Przy zmianie handle w Admin API (`update_product` w `shopify_client.py`) tworzony jest redirect `/products/{stary}` → `/products/{nowy}`; backfill: `cursor-api/scripts/backfill_product_handle_redirects.py`.

**Animacje biografii:** tło — crossfade w fazie wyjścia (0.88s); **tekst i portret** — zsynchronizowane z nagłówkiem karuzeli (`giclee:artist-showcase-enter` w `swapAndEnter`, ta sama animacja wejścia 0.88s). `prefers-reduced-motion` wyłącza efekt.

**Stabilność layoutu przy zmianie autora:** overlay-audit (grid, tło `inset:0`); stała wysokość **`.giclee-artist-bio`** w CSS (`--gab-hero-height: clamp(560px, 56svh, 640px)` — pas bio na desktopie; mobile v49: `height:auto`). **Scroll-overlap BIO → galeria:** `assets/giclee-bio-collection-scroll-stack.css` — BIO `sticky` (`z-index: 20`), galeria `relative` (`z-index: 30`), header obniżony do `10`; ładowane gdy włączone **Panel scroll** w sekcji galerii (`enable_scroll_panel`, domyślnie tak). Bez sztucznych spacerów ani listenerów scroll.

**Skrypty stanu** (`giclee-active-author.js`, `giclee-artist-biography.js`) ładują się **tylko z sekcji galerii**. Cache-bust: `&v=` (nie `?v=`).

**Biografia (Collection heading / Biografia autora):** `giclee-artist-biography.js` subskrybuje `GicleeActiveAuthor`. Boot biografii **po** `GicleeActiveAuthor.init()` w galerii.

**Nakładka tła biografii:** jeden asymetryczny overlay (`.giclee-artist-bio-bg__overlay` — lewa ciemniejsza pod tekst, środek/prawa odsłania kolaż; winieta w tej samej warstwie) **oraz** opcjonalna maska radialna ekspozycji (`.giclee-artist-bio-bg__radial-mask`, osobna warstwa nad gradientem). Przy metafield collage — theme overlay wyłączony. Fallback Theme Editor — ten sam gradient na `.overlay--solid`. Mobile: mocniejszy overlay. Portret: delikatna korekta `filter/box-shadow` w CSS. Treść `z-index: 2+`.

**Mobile galeria (≤749px):** mniejsze slajdy coverflow (`--gacs-slide-w/h`), padding `__inner` z `--page-margin`, nagłówek pełna szerokość, nawigacja autorów prev|next w jednym wierszu pod nagłówkiem, karuzela: viewport pełna szerokość + strzałki w drugim rzędzie stage. Na urządzeniach dotykowych autoplay karuzeli jest wyłączony, żeby slajd nie przestawiał się sam podczas oglądania; swipe działa także po rozpoczęciu gestu na linkowanej karcie.

**Warstwa tekstowa (overlay):** absolutnie pozycjonowane napisy — lewy dół: data / technika / gatunek aktywnego slajdu (SZCZEGÓŁY w `product.description`); prawy dół: cytat z listy `custom.collection_quotes` (GicleeApp → Cytaty; fallback `custom.collection_quote`). **Priorytet:** cytaty jeszcze nieobejrzane przez użytkownika (`localStorage`), potem los z pozostałych; po obejrzeniu wszystkich — cykl od początku. Przy zmianie autora wybór utrzymywany do kolejnej zmiany autora. Pliki: `assets/giclee-showcase-slide-overlays.{css,js}`. Przy zmianie autora: **fade off** dopiero gdy pojawia się nowe tło Karuzela2 (`giclee:karuzela2-artist-bg-enter`, ~680 ms), **fade on** po podmianie tracku galerii. Kolejka reveal nie jest kasowana przed końcem fade off (overlay JS v13-unseen). Desktop/tablet; na mobile ukryte.

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

**v49 (2026-07-01):** jasna obwódka przy własnym tle BIO (pierwsze załadowanie / upload) — inna przyczyna niż sam `.section-background`: (1) `scroll-stack` ustawiał `background-color: var(--color-background)` na `.custom-section-background`; (2) subpixel przy `sticky` + `translateZ(0)` na szwie góra/dół hero; (3) inline script szukał `.giclee-artist-biography-section` wewnątrz hosta (`querySelector` bez matcha na samym `#shopify-section`). Fix: `#000` przy `--custom-bg`, bleed tła `top:-2px` / `bottom:-4px`, `visibility:hidden` na `[data-gab-custom-bg]` do `img.onload`, poprawiony inline script (`host` = sekcja).

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
