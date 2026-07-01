# Troubleshooting — motyw (pusty)

Hub motywu: [`README.md`](README.md)  
Macierz cross-warstwowa: [`../zaleznosci.md`](../zaleznosci.md)

Objawy UI, layout, deploy motywu. Worker / OAuth → [`../../cursor-api/docs/troubleshooting.md`](../../cursor-api/docs/troubleshooting.md).

---

## Mockup / layout

| Objaw | Plik |
|-------|------|
| Czarny prostokąt zamiast ramki | `#pm-frame` bez `src` — `giclee-photo-mockup.liquid` + `setFrame()` |
| Nie mieści się w pionie (laptop) | `giclee-photo-mockup.css` 1024–1400 + `syncPmMockupCenterUi` |
| Zoom za blisko mockupu (desktop) | `mockupClear` w `giclee-photo-mockup.js` |
| Suwak pod menu header | `assets/custom.css` — nie dodawać `overflow-x: auto` na menu |
| Menu hamburger nie widać (mobile, własna fotografia) | Mockup `z-index: 60` zasłaniał drawer (`18`) — mobile: sekcja mockup `z-index: 4`, drawer `70` w `theme.liquid` |
| Lewy panel konfiguratora ukryty (mobile PDP) | Desktop: `top: --pm-mockup-center-y`; mobile **po uploadzie**: pionowy stos w `giclee-photo-mockup.css` (`max-width: 980px`, `#pm-hero.loaded`) |
| Po uploadzie elementy na siebie (mobile) | Układ w flow: mockup → hint → shop → `#pm-left-rail`; wyłączone `transform: scale` i absolutne pozycje paneli |
| Brak pinch-zoom na telefonie | `giclee-photo-mockup.js` — `activePointers` + `beginPinchGesture()` na `#pm-canvas`; `touch-action: none` po `loaded` |
| Dużo czerni pod mockupem (mobile PDP) | `min-height: 0` po `loaded`; `display: none` na `.pm-hero-ui` i `.pm-side-shop:not(.is-visible)`; mniejsze paddingi sekcji |
| Scroll mockupu „nie łapie” (mobile PDP) | Wyłączone sprzężenie scroll→animacja UI (`disableMobilePdpScrollCoupling`); przed uploadem `pointer-events: none` na mockupie, tylko `.pm-upload-btn` klikalny |
| Panel jakości pusty | `layout/theme.liquid` → `initPmQualityPanel`, event `pm-image-loaded` |
| Po „Dodaj do koszyka” brak scrollu / koszyk za wcześnie | Kolejność: `pmScrollPageToTopForCart` → dopiero `pmOpenCartDrawer` — [`mockup-wlasna-fotografia.md`](mockup-wlasna-fotografia.md) |
| Scroll cofa się do mockupu po dodaniu | Auto-centrowanie przy hover — `pmPauseMockupAutoScroll` / `pmCartScrollLock` w `giclee-photo-mockup.js` |
| Stary flow (Przygotowanie… / Dodawanie…) | Usunięte — przycisk zostaje „Dodaj do koszyka”; upload w tle |

→ [`mockup-wlasna-fotografia.md`](mockup-wlasna-fotografia.md) · [`../jakosc-wydruku/README.md`](../jakosc-wydruku/README.md)

---

## Upload / koszyk (front)

| Objaw | Przyczyna |
|-------|-----------|
| Brak uploadId | `pmPrepareOrderUpload` fail — konsola przeglądarki |
| Brak dodania do koszyka (mobile PDP) | Otwórz konfigurator → „Dodaj do koszyka” pod opcjami; drawer dopiero po uploadzie + `/cart/add.js` (`theme.liquid` `pmAddConfiguredToCart`) |
| Stary JS | Hard refresh / bump `?v=` w `giclee-photo-mockup.liquid` (obecnie `mobile-cart-fix-20260605`) |
| Błąd przy dodaniu do koszyka | `layout/theme.liquid` — hook `properties[_Upload ID]`, `pmAddConfiguredToCart` |
| Koszyk otwarty, strona nie na górze | Drawer (`dialog.js`) blokuje scroll — nie otwierać koszyka przed `pmScrollPageToTopForCart` |

Backend (CORS, 413): [`../../cursor-api/docs/troubleshooting.md`](../../cursor-api/docs/troubleshooting.md)

---

## Zoom HD (karta produktu)

| Objaw | Plik |
|-------|------|
| Brak viewer | Metafield `custom.zoom_manifest` |
| Viewer bez kafelków | [`produkt-i-zoom.md`](produkt-i-zoom.md) + `dodajobraz` zoom |

---

## Shopify theme push

```powershell
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live --only "ścieżka"
```

Zły motyw → ID `197314249052` w Admin → Motywy.

Motyw live: **Kopia Giclee Art Br**.

---

## Breakpointy (przypomnienie)

| Szerokość | Układ |
|-----------|--------|
| `< 1024px` | Stack pod mockupem |
| `1024–1400px` | Laptop, `100vh` fit |
| `> 1400px` | Desktop, większy odstęp mockup → zoom |
