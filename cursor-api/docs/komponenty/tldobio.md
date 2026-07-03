# Tło do Bio (`tldobio`)

Komponent GicleeApp: upload tła sekcji **Biografia autora** per kolekcja Shopify.

## UI

- Launcher → **Administracja strony** → **Tło do Bio**
- Lista kolekcji (filtr, tylko z/bez tła)
- **Przeciągnij grafikę** na podgląd lub **Wgraj tło…**; suwak / strzałki / przeciągnięcie — kadr poziomy; suwak **Przyciemnienie** 0–100% + **Wyłącz przyciemnienie**; checkbox **Lekkie powiększenie kadru (scale 1.04)**; przycisk **Gradient** (menu: **Bez gradientu** / **Gradient wąski** / **Gradient szeroki** / **Gradient szeroki + dół** / **Gradient szeroki v2** / **Gradient szeroki v3** / **Gradient szeroki v3 + dół**); sekcja **Maska radialna (ekspozycja)** — włącz/wyłącz, środek (X/Y, podwójne kliknięcie podglądu), rozmiar elipsy, wtapianie, ekspozycja; **Zapisz ustawienia tła**
- Podgląd **z tekstem BIO** (nagłówek + fragment opisu kolekcji); proporcje i overlay jak sekcja BIO na desktopie (`preview_render.py` = ten sam compositing co CSS motywu)
- Panel ustawień pod podglądem ma **przewijanie pionowe** (pasek + kółko myszy) — maska radialna i przyciski na dole nie giną przy niższym oknie
- Usuń tło, otwórz stronę kolekcji
- Wymaga `tkinterdnd2` (`pip install tkinterdnd2`) — bez pakietu działa tylko wybór pliku z dysku

## Persystencja

| Warstwa | Lokalizacja |
|---------|-------------|
| Shopify Files | CDN URL obrazu |
| Metafield kolekcji | `custom.bio_background_url` (type `url`, storefront `PUBLIC_READ`) |
| Pozycja pozioma | `custom.bio_background_pos_x` (0–100, domyślnie 50 — `object-position: X% center`) |
| Przyciemnienie | `custom.bio_background_overlay_pct` (0–100, domyślnie 100 — `opacity` gradientu overlay) |
| Powiększenie kadru | `custom.bio_background_cover_scale` (boolean — `transform: scale(1.04)` na obrazie tła) |
| Maska radialna | `custom.bio_background_radial_mask` (JSON — osobna warstwa ekspozycji obok gradientu pod tekst; pola: `enabled`, `cx`, `cy`, `rx`, `ry`, `feather`, `exposure`) |
| Gradient u góry (menu) | `custom.bio_background_menu_gradient` (`none` \| `narrow` \| `wide` \| `wide_bottom` \| `wide_v2` \| `wide_v3` \| `wide_v3_bottom`; domyślnie `wide`; `wide_bottom` jak szeroki + ten sam pas u dołu; `wide_v2` bez płaskiej czerni u góry; `wide_v3` jak v2, wysokość pasu 60%; `wide_v3_bottom` jak v3 + dół) |
| Cache lokalny | `Komponenty/tldobio/data/collections.json` — mapowanie `handle → url` + snapshot listy (`catalog`) |

**Jakość obrazu:** upload idzie do Shopify Files jako plik binarny (`contentType: FILE`, bez przecompressowania MediaImage). Motyw żąda `width=3840` z CDN. Zalecane min. **2560 px** szerokości źródła (PNG lub wysokiej jakości JPG); powyżej 4472 px skalujemy lokalnie przed wysłaniem (jakość 95). Istniejące tła wgrane wcześniej — **wgraj ponownie**, żeby skorzystać z nowego trybu.

**Wydajność:** lista kolekcji + metafield tła w **jednym** przebiegu GraphQL (do 250 kolekcji na stronę). Przy starcie UI pokazuje ostatni snapshot z cache, potem odświeża w tle.

Przy pierwszym uploadzie komponent tworzy definicję metafield (GraphQL `metafieldDefinitionCreate`).

## Motyw (storefront)

- JSON autorów: `snippets/giclee-artist-showcase-artist-json.liquid` → `bioBackgroundUrl`, `bioBackgroundPosX`, `bioBackgroundMenuGradient`, `bioBackgroundRadialMask`
- Sekcja: `sections/giclee-artist-biography.liquid` — SSR z metafield bieżącej kolekcji
- JS: `assets/giclee-artist-biography.js` → `applyBackground()` przy zmianie autora (karuzela)
- CSS: `assets/giclee-artist-biography.css` — overlay premium (gradient pod tekst) + opcjonalna `.giclee-artist-bio-bg__radial-mask`; mobile ciemniejszy overlay

**Fallback:** brak metafield → tło z ustawień sekcji (`background_image` w Theme Editor).

**Kreator kolaży:** [`kolaz.md`](kolaz.md) — zaawansowane składanie grafiki + przycisk «→ Tło BIO».

## Wymagania Shopify

- Scope: `write_files`, metafieldy kolekcji
- Sesja: jak inne komponenty (`dodajobraz/shopify_client.load_session()`)

## Powiązane

- [`../../docs/motyw/kolekcja-autora-showcase.md`](../../docs/motyw/kolekcja-autora-showcase.md) — sekcja BIO + karuzela
- [`przedpo.md`](przedpo.md) — wzorzec uploadu + metafield
