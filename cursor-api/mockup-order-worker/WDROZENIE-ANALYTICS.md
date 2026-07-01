# Wdrożenie analityki ruchu (Worker + D1)

> Ten sam Worker co mockupy: `giclee-mockup-orders`  
> Collect URL: `https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/analytics/collect`

Pixel zbiera eventy ze sklepu → **Cloudflare D1**. Dashboard w GicleeApp pobiera je przyciskiem **Sync z chmury**.

---

## Krok 1 — secret (już masz w `.env`)

W `cursor-api/.env`:

```env
ANALYTICS_COLLECT_SECRET=…
ANALYTICS_COLLECT_URL=https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/analytics/collect
```

Ten sam secret musi trafić na Workera (krok 3).

---

## Krok 2 — baza D1 + migracja

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
npx wrangler login
npx wrangler d1 create giclee-analytics
```

Skopiuj **`database_id`** z outputu i wklej w `wrangler.toml` zamiast `REPLACE_AFTER_D1_CREATE`:

```toml
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Zastosuj schemat:

```powershell
npx wrangler d1 migrations apply giclee-analytics --remote
```

---

## Krok 3 — secret na Workerze + deploy

```powershell
npx wrangler secret put ANALYTICS_COLLECT_SECRET
# wklej TEN SAM ciąg co ANALYTICS_COLLECT_SECRET w cursor-api/.env

npm run deploy
```

Sprawdź:

```powershell
curl https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/analytics/stats
```

(Odpowiedź bez secret może być 401 — to OK; po deploy z D1 health pokaże `analytics: true`.)

---

## Krok 4 — Custom Pixel w Shopify

1. Shopify Admin → **Ustawienia → Dane klienta → Pixeli klienta → Dodaj niestandardowy**
2. Skopiuj kod z dashboardu GicleeApp → zakładka **Konfiguracja**
3. W pixelu ustaw:
   - `COLLECT_URL` = URL z kroku 1
   - `COLLECT_SECRET` = ten sam secret co w `.env`
4. Zapisz pixel

Wejdź na `gicleeart.eu` → w dashboardzie (po **Sync z chmury**) powinny pojawić się eventy.

---

## Krok 5 — dashboard lokalny

1. GicleeApp → **Analiza ruchu** → uruchom dashboard
2. **Sync z chmury** — pobiera eventy z D1 do PC
3. Przeglądaj KPI, kraje, lejek

Możesz robić Sync z chmury codziennie — sklep zbiera dane 24/7 bez włączonego PC.

---

## Endpointy (Worker)

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| POST | `/api/analytics/collect` | Pixel Shopify (secret w nagłówku lub JSON `secret`) |
| GET | `/api/analytics/export` | Export do GicleeApp (nagłówek `X-Analytics-Secret`) |
| GET | `/api/analytics/stats` | Liczba eventów w chmurze |

---

## Test collect (PowerShell)

```powershell
$secret = "TWOJ_SECRET"
$body = @{
  event_id = "manual_test_1"
  event_name = "page_viewed"
  timestamp = (Get-Date).ToUniversalTime().ToString("o")
  visitor_id = "test_v1"
  session_id = "test_s1"
  url = "https://gicleeart.eu/pl-pl"
  shop_domain = "gicleeart.eu"
  consent_status = "granted"
  user_agent = "Mozilla/5.0 Chrome/120 Safari/537.36"
  secret = $secret
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://giclee-mockup-orders.eagleblastmusic.workers.dev/api/analytics/collect" `
  -Method POST -ContentType "application/json" -Body $body
```

Potem w dashboardzie: **Sync z chmury**.
