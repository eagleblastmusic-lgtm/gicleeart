# Tło do Bio (`tldobio`)

Komponent GicleeApp: upload tła sekcji **Biografia autora** per kolekcja Shopify.

## UI

- Launcher → **Marketing** → **Tło do Bio**
- Lista kolekcji (filtr, tylko z/bez tła)
- **Przeciągnij grafikę** na podgląd lub **Wgraj tło…**; suwak / strzałki / przeciągnięcie — kadr poziomy; suwak **Przyciemnienie** 0–100% + **Wyłącz przyciemnienie**; checkbox **Lekkie powiększenie kadru (scale 1.04)**; sekcja **Maska radialna (ekspozycja)** — włącz/wyłącz, środek (X/Y, podwójne kliknięcie podglądu), rozmiar elipsy, wtapianie, ekspozycja; **Zapisz ustawienia tła**
- Podgląd **z tekstem BIO** (nagłówek + fragment opisu kolekcji); proporcje i overlay jak sekcja BIO na desktopie (`preview_render.py` = ten sam compositing co CSS motywu)
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
| Cache lokalny | `Komponenty/tldobio/data/collections.json` — mapowanie `handle → url` + snapshot listy (`catalog`) |

**Wydajność:** lista kolekcji + metafield tła w **jednym** przebiegu GraphQL (do 250 kolekcji na stronę). Przy starcie UI pokazuje ostatni snapshot z cache, potem odświeża w tle.

Przy pierwszym uploadzie komponent tworzy definicję metafield (GraphQL `metafieldDefinitionCreate`).

## Motyw (storefront)

- JSON autorów: `snippets/giclee-artist-showcase-artist-json.liquid` → `bioBackgroundUrl`, `bioBackgroundPosX`, `bioBackgroundRadialMask`
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
