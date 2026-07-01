# mockup-order-worker

Hub warstwy API: [`../README.md`](../README.md)

**URL:** `https://giclee-mockup-orders.eagleblastmusic.workers.dev`  
**Kod:** `mockup-order-worker/src/index.js`  
**Konfig:** `mockup-order-worker/wrangler.toml`  
**Wdrożenie krok po kroku:** [`../../mockup-order-worker/WDROZENIE.md`](../../mockup-order-worker/WDROZENIE.md)

---

## Endpointy

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| POST | `/api/mockup-upload` | Upload plików (normalny lub `stage_only=1`) |
| POST | `/webhooks/shopify/orders-paid` | Webhook Shopify → e-mail |
| GET | `/health` | `{ ok: true, analytics: bool }` |
| POST | `/api/analytics/collect` | Pixel → D1 |
| GET | `/api/analytics/export` | Export (secret) |
| GET | `/api/analytics/stats` | Statystyki D1: `total_events`, `events_today` (UTC), `bot_events`, `last_event_at` |

Wdrożenie analityki: [`../../mockup-order-worker/WDROZENIE-ANALYTICS.md`](../../mockup-order-worker/WDROZENIE-ANALYTICS.md)

---

## Upload — pola FormData

| Pole | Opis |
|------|------|
| `original` | Surowy plik od klienta |
| `original_full` | JPEG pełnej rozdzielczości (opcjonalnie) |
| `preview` | Podgląd mockupu JPG |
| `crop` | JSON kadrowania |
| `config` | JSON ramki (dąb, kolor ramy, rozmiar M/L/XL, passepartout) |
| `meta_extra` | JSON (wymiary, mobile, bytes) |
| `stage_only=1` | Tylko `original` + `uploadId` (telefon, w tle) |
| `upload_id` + `complete_staged=1` | Dokończenie staged uploadu |

Pliki w R2 (bucket `giclee-zoom`, prefix `customer-uploads/{uuid}/`):

- `original.{ext}`, `original-full.jpg`, `preview.jpg`, `crop.json`, `meta.json`

Publiczne URL: `PUBLIC_BASE_URL` w `wrangler.toml` (R2 public bucket).

---

## E-mail po opłaceniu

1. Shopify wysyła webhook **Orders paid**
2. Worker szuka linii z `_Upload ID` w properties
3. Czyta `meta.json` z R2 (w tym `config.passepartout` i property `Passepartout`)
4. Resend → `MERCHANT_EMAIL` (`gicleeartpl@gmail.com`)
5. From PL: `zamowienia@gicleeart.eu`, intl: `orders@gicleeart.eu`

Przy błędzie Resend Worker zwraca **502** (nie cicho 200).

---

## Sekrety i zmienne

**Vars (`wrangler.toml`):** `MERCHANT_EMAIL`, `PUBLIC_BASE_URL`, `ALLOWED_ORIGINS`, `RESEND_FROM_PL`, `RESEND_FROM_INTL`

**Secrets:** `RESEND_API_KEY`, `SHOPIFY_WEBHOOK_SECRET` (= Client secret aplikacji Shopify / `SHOPIFY_API_SECRET` w `.env`)

---

## Rejestracja webhooka

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
python scripts/register_webhook.py
```

Bez webhooka zamówienia nie wywołują maila.

---

## Test maila / ponowne wysłanie

`scripts/resend_order_email.py` — wymaga nagłówka `User-Agent: Shopify-Captain-Hook` (Cloudflare 1010).

---

## Deploy

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
npm install
npx wrangler deploy
```

---

## Zależności zewnętrzne (inne warstwy)

| Warstwa | Powiązanie |
|---------|------------|
| **pusty** | [`assets/giclee-photo-mockup.js`](../../../assets/giclee-photo-mockup.js) → POST upload, scroll → koszyk; [`layout/theme.liquid`](../../../layout/theme.liquid) → `_Upload ID`, `pmAddConfiguredToCart` |
| **Integracja** | [`../../../docs/zaleznosci.md`](../../../docs/zaleznosci.md) |

Powiązany front: [`../../../docs/motyw/mockup-wlasna-fotografia.md`](../../../docs/motyw/mockup-wlasna-fotografia.md)
