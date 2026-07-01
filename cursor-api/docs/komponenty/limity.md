# Limity usług

**Folder:** `Komponenty/limity/`  
**Tryb GicleeApp:** `inline` · sekcja launcher: **Narzędzia pomocnicze** (pierwszy kafelek)

Dashboard zużycia i limitów zewnętrznych usług — jeden ekran zamiast rozproszonego sprawdzania paneli.

---

## Co pokazuje

| Sekcja | Źródło danych |
|--------|----------------|
| **Cloudflare R2 + Worker** | API bucket + opcjonalnie `CLOUDFLARE_API_TOKEN` (Class A/B); **analityka** — `GET /api/analytics/stats` (eventy dziś vs ~100k/d Free) |
| **Resend** | Paginacja GET `/emails` + quota z `.env` (wymaga **Full access** klucza w `.env`) |
| **SerpAPI** | `account.json` (wymaga `SERPAPI_KEY`) |
| **Meta (Cykl)** | `debug_token` + `meta_credentials.json` · przycisk **Odnów tokeny** |
| **Shopify, NBP, Vercel** | Stałe progi z [`USLUGI.md`](../../../USLUGI.md) + link do panelu |

Auto-odświeżanie co 5 minut. Scroll kółkiem myszy — `_bind_wheel_to_scroll_children` (re-bind po każdym `render()`).

---

## Konfiguracja `.env`

```env
# Cloudflare R2 — jak w dodajobraz (R2_*, opcjonalnie CLOUDFLARE_API_TOKEN)
CLOUDFLARE_API_TOKEN=...

# Resend — Full access (send-only daje 401 w Limity; Worker może mieć send-only osobno)
RESEND_API_KEY=re_...
RESEND_MONTHLY_QUOTA=3000
RESEND_DAILY_QUOTA=100

# SerpAPI
SERPAPI_KEY=...
SERPAPI_MONTHLY_QUOTA=100

# Analityka (licznik eventów na Workerze — jak w module Analiza ruchu)
ANALYTICS_COLLECT_URL=https://…workers.dev/api/analytics/collect
ANALYTICS_COLLECT_SECRET=...

# Meta (dokładniejszy debug_token — opcjonalnie)
META_APP_ID=...
META_APP_SECRET=...
```

Brak klucza ≠ błąd — sekcja pokazuje znany limit planu i podpowiedź konfiguracji.

**Resend vs Worker:** klucz w `wrangler secret` może być send-only; do Limity skopiuj osobny klucz **Full access** z panelu Resend.

**Meta:** Page tokeny często nie mają daty wygaśnięcia — Limity pokazuje «bez daty (OK)». Kreator **Odnów tokeny** → [`meta-tokeny.md`](meta-tokeny.md).

---

## Pliki

| Plik | Rola |
|------|------|
| `view.py` | UI z paskami postępu, przycisk Meta **Odnów tokeny** |
| `collectors.py` | Pobieranie danych z API (`USER_AGENT` w requestach HTTP) |
| `env_config.py` | Odczyt `.env` |

Powiązane Meta: [`../socialmedia/cykl/meta_token_status.py`](../../Komponenty/socialmedia/cykl/meta_token_status.py), [`meta_renew_wizard.py`](../../Komponenty/socialmedia/cykl/meta_renew_wizard.py)

Powiązane R2: [`dodajobraz/cloudflare_usage_dialog.py`](../dodajobraz/cloudflare_usage_dialog.py) (szczegóły R2 w dodajobraz).

---

## Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| R2: błąd bucketu | Sprawdź `R2_*` w `.env` |
| Class A/B: brak danych | Dodaj `CLOUDFLARE_API_TOKEN` (Analytics / R2 Read) |
| Resend: HTTP 403 | Brak User-Agent — naprawione w `collectors.py`; zrestartuj GicleeApp |
| Resend: HTTP 401 restricted | Klucz send-only — w `.env` ustaw **Full access** |
| Resend: brak licznika mimo OK | Licznik z listy `/emails`, nie z nagłówków — sprawdź Full access |
| SerpAPI: błąd klucza | `SERPAPI_KEY` w `.env` |
| Meta: wygasłe tokeny | **Odnów tokeny** → [`meta-tokeny.md`](meta-tokeny.md) |
| Scroll kółkiem nie działa | Znany fix: re-bind wheel po renderze w `view.py` |
