# Losuj Obraz — Fine Art Oracle (WebGL)

Strona „Losuj Obraz”: użytkownik klika „Losuj obraz”, scena WebGL (Three.js) losuje realny produkt z widowiskową animacją (Museum Portal), a wynik pokazuje się w karcie HTML/CSS. Fallback CSS dla braku WebGL / reduced-motion / słabych urządzeń.

## Pliki

| Plik | Rola |
|------|------|
| `templates/page.losuj-produkt.json` | Szablon strony (handle `losuj-produkt`); podpina sekcję |
| `sections/giclee-random-artwork.liquid` | HTML sceny + schema (teksty, pula, `enable_webgl`, `fetch_full_pool`) |
| `snippets/giclee-random-artwork-pool.liquid` | Startowa pula realnych produktów → JSON (warstwa 1) |
| `assets/giclee-random-artwork.js` | Kontroler: dane, losowanie, maszyna stanów, capability gate, lifecycle |
| `assets/giclee-random-artwork-webgl.js` | Scena Three.js: portal, karty, pył, kamera, reveal, teardown |
| `assets/giclee-random-artwork.css` | Layout premium + stany (`idle/loading/drawing/result/error`, `grw--webgl`) |
| `assets/three.module.js` | Lokalny build Three.js r160 (ESM), ładowany dynamicznie |

## Pobieranie produktów

- Warstwa 1 (Liquid): `collections.all`, maks. 50 (limit Shopify), embed w `<script data-grw-pool>`. Zawsze działa.
- Warstwa 2 (AJAX): `{{ routes.root_url }}/collections/all/products.json?limit=250&page=N`, paginacja do 20 stron; scala po URL, liczy dostępność z wariantów. Błąd/blokada → zostaje warstwa 1.
- Finalny zwycięzca: losowany z pełnej puli (`pickWinner`, preferuje `available`, unika powtórki). Próbka w scenie: 16 desktop / 8 mobile, losowana na nowo co rundę.

## WebGL (kiedy startuje)

`shouldUseWebGL()` = `enable_webgl` ON **i** brak `prefers-reduced-motion` **i** jest WebGL **i** `deviceMemory >= 2`. Three.js importowany jest dynamicznie dopiero po pierwszym kliknięciu — nigdy globalnie, nigdy na innych stronach.

Lifecycle sceny: init (renderer DPR≤1.5/1.25, fog, portal, pył, karty z preloadem tekstur) → animate ~5.4 s desktop / 4.8 s mobile (wejście → orbit → spowolnienie → wybór → reveal, landing winnera liczony deterministycznie) → `onComplete` → karta wyniku HTML → teardown (stop `rAF`, dispose geometrii/materiałów/tekstur, `renderer.dispose()`+`forceContextLoss()`, usunięcie canvasu). Obsługa `resize` (+ `ResizeObserver`) i `webglcontextlost` (→ wynik + teardown).

## Fallback CSS

Gdy WebGL off: portal CSS (`assets/giclee-random-artwork.css`) + narracyjne teksty fazowe; przy `prefers-reduced-motion` skrócona sekwencja. Wynik, tytuł, zdjęcie i CTA zawsze w HTML/CSS.

## Wyłączanie / ustawienia

W edytorze sekcji „Losuj Obraz — oracle”:
- „Włącz efekt WebGL (Three.js)” (`enable_webgl`, domyślnie ON) → OFF zostawia wariant CSS.
- „Doczytaj pełną pulę (AJAX)” (`fetch_full_pool`, domyślnie ON) → OFF, gdy sklep blokuje `products.json` (zostaje pula z Liquid).
- Kolekcja źródłowa (puste = wszystkie), teksty, schemat kolorów.
- Własne tło: `background_image` / `background_video` (film ma priorytet); puste = domyślna scena.
- Parallax tła (`background_parallax`): subtelny ruch obrazu lub filmu przy ruszaniu kursorem (jak konfigurator PDP).

## Dopasowanie do ekranu (bez scrolla)

Na desktopie (`min-width: 750px`) strona nie scrolluje się — header + scena + stopka mieszczą się w oknie. Realizacja: wzorzec sticky-footer na flexboxie, scoped `body:has(.giclee-random-artwork)` w `assets/giclee-random-artwork.css`. Scena (`__scene`) ma wtedy `flex:1; min-height:0`, więc tło i animacja skalują się do dostępnej wysokości (nadpisuje `min-height: clamp(640px, 92svh, 1000px)`). Na mobile (`max-width: 749px`) zostaje naturalny układ, by nie przycinać dużego nagłówka.

Dotyczy to wszystkich stanów, także wyniku: `__content` dostaje `grid-template-rows: minmax(0,1fr)`, a karta wyniku skaluje obraz (`__frame-mat` flex, `__result-image { max-height:100% }`) do miejsca pozostałego po tytule i CTA — dzięki temu po wylosowaniu obrazu strona nadal się mieści bez scrolla.

## Test przed publikacją

- Desktop: pełna scena; mobile: wariant uproszczony; sprawdź brak przycięcia obrazu/CTA.
- DevTools → Rendering → „Emulate prefers-reduced-motion” → fallback.
- Ponowne losowanie 5–10×, szybkie klikanie (jedna scena naraz), resize w trakcie, DevTools throttling.
- Konsola bez błędów; po reveal brak aktywnego `requestAnimationFrame` (Performance/Memory).
- Tytuł wyniku: warianty w nawiasach `(lub …)` (także zagnieżdżone, np. `(lub … (1866))`) są obcinane w `giclee-random-artwork.js` (`primaryProductTitle`) — wyświetla się tylko tytuł podstawowy.

## Po `shopify theme push`

Wypchnij: `assets/giclee-random-artwork.js|css`, `assets/giclee-random-artwork-webgl.js`, `assets/three.module.js`, `sections/giclee-random-artwork.liquid`, `snippets/giclee-random-artwork-pool.liquid`, `templates/page.losuj-produkt.json`. Po zmianie JS/CSS bump `?v=…` w sekcji. Sprawdź na live stronę `/pages/losuj-produkt` (desktop + mobile, konsola).
