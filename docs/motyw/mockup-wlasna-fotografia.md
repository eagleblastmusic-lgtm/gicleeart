# Mockup — własna fotografia klienta

Flow: klient wgrywa zdjęcie → kadruje w ramce → konfiguruje drewno/kolor/rozmiar → dodaje do koszyka → po opłaceniu Worker wysyła mail z linkami do plików w R2.

**Worker (backend):** [`../../cursor-api/docs/worker/mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md)  
**Jakość PPI:** [`../jakosc-wydruku/README.md`](../jakosc-wydruku/README.md)  
**Mapa zależności:** [`../zaleznosci.md`](../zaleznosci.md)

---

## Pliki (kolejność ładowania)

| Plik | Rola |
|------|------|
| `snippets/giclee-photo-mockup.liquid` | HTML mockupu, URL API, cache-bust CSS/JS |
| `assets/giclee-photo-mockup.js` | Ramka, zoom, pan, upload, auto-centrowanie scroll, `pmPrepareOrderUpload`, `pmScrollPageToTopForCart` |
| `assets/giclee-photo-mockup.css` | Wygląd, breakpointy laptop/desktop |
| `layout/theme.liquid` | `#pm-config`, `#pm-left-rail`, `#pm-quality-panel`, `pmAddConfiguredToCart`, hook koszyka |
| `lib/giclee-print-analysis/giclee-print-analysis.js` | Werdykt PPI (ładowany z motywu) |

Snippet renderowany z:

- `templates/page.fotografia-obraz.json`
- `snippets/product-information-content.liquid` (szablon produktu własna fotografia)

---

## Przepływ „Dodaj do koszyka” (UI)

Po kliknięciu **Dodaj do koszyka** w `#pm-side-shop` (przycisk `#pm-config-add-to-cart`), gdy walidacja przejdzie (zdjęcie, wariant):

```
[Klik — walidacja OK]
    → pmPauseMockupAutoScroll(8 s)
    → pmPrepareOrderUpload → POST /cart/add.js → cart:update
    → pmHideConfiguratorUi() + pmScrollPageToTopForCart() + pmOpenCartDrawer() — dopiero po sukcesie
```

**Kolejność jest ważna:** drawer koszyka ustawia `body { position: fixed }` — otwarcie przed uploadem/koszykiem mogło przerywać fetch na iOS; drawer otwiera się dopiero gdy pozycja jest w koszyku.

Przy błędzie (brak zdjęcia, niedostępny wariant, upload fail) scroll i koszyk **nie** uruchamiają się — krótki komunikat na przycisku.

Implementacja:

| Warstwa | Funkcja / element |
|---------|-------------------|
| `layout/theme.liquid` | `pmAddConfiguredToCart`, `pmShowCartUiImmediately`, `pmOpenCartDrawer`, `pmWaitThenOpenCart` (fallback) |
| `assets/giclee-photo-mockup.js` | `pmScrollPageToTopForCart`, `pauseMockupAutoScroll`, `scrollMockupToViewportCenter` |

Cache-bust JS/CSS (2026-06): `?v=mobile-cart-fix-20260605` w `giclee-photo-mockup.liquid`.

---

## Auto-centrowanie mockupu (scroll strony)

Przy najechaniu na ramkę mockup może przewinąć stronę tak, by mockup był bliżej środka viewportu (`scrollMockupToViewportCenter`). To kolidowało z flow koszyka — po scrollu na górę mechanizm cofał stronę do mockupu.

**Ochrona przy dodawaniu do koszyka:**

- `window.pmPauseMockupAutoScroll(ms)` — tymczasowo blokuje auto-scroll i kasuje timery layoutu
- `window.pmCartScrollLock` — flaga na czas sekwencji scroll → koszyk
- event `pm-config-add-to-cart` na `#pm-hero` — wywoływany synchronicznie na początku kliknięcia

---

## Przepływ uploadu

```
[Wybór pliku]
    → loadPhotoFromFile() — createImageBitmap (pełna rozdzielczość)
    → stageRawUploadOnMobile() — opcjonalnie surowy plik od razu (telefon)

[Dodaj do koszyka]
    → (UI: scroll na górę + panel koszyka — patrz sekcja wyżej)
    → pmPrepareOrderUpload(frameConfig) — równolegle w tle
    → POST Worker /api/mockup-upload
         original (surowe bajty)
         original_full (JPEG max jakość, HEIC/WebP/mobile)
         preview (mockup JPG)
         crop.json, config, meta_extra
    → uploadId w koszyku: properties[_Upload ID]
    → passepartout: properties[Passepartout] (Biały / Czarny, bez wpływu na cenę)

[Zapłacone zamówienie]
    → Shopify webhook orders/paid → Worker → Resend → gicleeartpl@gmail.com
```

---

## API w przeglądarce

| Global | Opis |
|--------|------|
| `window.pmPrepareOrderUpload(config)` | Upload przed dodaniem do koszyka; zwraca `{ uploadId }` |
| `window.pmHasMockupImage()` | Czy jest wgrane zdjęcie |
| `window.pmFrameConfig` | `{ wood, color, size, passepartout }` z konfiguratora |
| `window.pmPauseMockupAutoScroll(ms)` | Wyłącza auto-centrowanie mockupu na N ms |
| `window.pmScrollPageToTopForCart()` | Promise: scroll na górę strony przed otwarciem koszyka |

Eventy na `#pm-hero`:

- `pm-image-loaded` — wymiary pliku, orientacja
- `pm-view-change` — zoom/kadrowanie (PPI kadru)
- `pm-config-change` — rozmiar M/L/XL
- `pm-config-add-to-cart` — start flow koszyka (wywoływany przed `pmAddConfiguredToCart`)
- `pm-pause-mockup-scroll` — alternatywny trigger wyciszenia auto-scrollu
- `pm-side-shop-update` — synchronizacja pozycji panelu ceny/koszyka

---

## Upload URL

Domyślnie w snippecie:

`https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/mockup-upload`

Nadpisanie: **Motyw → Ustawienia → Mockup — własna fotografia** (`settings.pm_upload_api_url`).

---

## Jakość zdjęcia (mobile)

- Surowy plik: `arrayBuffer` → `original` w R2 bez rekompresji w JS
- `original-full.jpg`: pełna rozdzielczość z `createImageBitmap` (HEIC/WebP, mobile)
- W panelu „Jakość wydruku”: wymiary `714×953 · 0.7 MP · 47 KB` (z `pm-image-loaded`)

Limit: **50 MB** na plik.

---

## Layout UI

| Element | ID / klasa |
|---------|------------|
| Mockup | `#pm-hero`, `.pm-mockup-shell`, `#pm-wrapper` |
| Zoom pionowy | `.pm-zoom-rail` |
| Sterowanie | `.pm-hint` |
| Cena + koszyk | `#pm-side-shop`, `#pm-config-add-to-cart` |
| Konfigurator (lewo) | `#pm-left-rail`, `#pm-config` |
| Jakość wydruku | `#pm-quality-panel` |

Zmienne CSS ustawiane w JS: `--pm-zoom-left`, `--pm-hint-left`, `--pm-side-scale`, `--pm-shop-left`.

---

## Deploy

Patrz [`README.md`](README.md) w tym folderze — `shopify theme push` z `--only` na pliki mockupu.

Worker osobno: [`../../cursor-api/docs/worker/mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md).

---

## Zależności zewnętrzne

| Element | Warstwa | Plik / URL |
|---------|---------|------------|
| Upload API | **cursor-api** | Worker `POST /api/mockup-upload` — [`mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md) |
| URL w motywie | **pusty** | `settings.pm_upload_api_url` w `config/settings_schema.json` |
| Property koszyka | **pusty** | `properties[_Upload ID]`, `properties[Passepartout]` w `layout/theme.liquid` |
| Drawer koszyka | **pusty** | `assets/cart-drawer.js` + `assets/dialog.js` — `position: fixed` na body przy otwarciu |
| Pliki klienta | **cursor-api** | R2 `giclee-zoom` / `customer-uploads/{uuid}/` |
| E-mail po zakupie | **cursor-api** | Webhook `orders/paid` → Resend |
