# Zależności wewnętrzne (cursor-api)

Hub warstwy API: [`README.md`](README.md)  
Mapa cross-warstwowa: [`../../docs/zaleznosci.md`](../../docs/zaleznosci.md)

---

## Pliki konfiguracyjne

| Plik | Kto czyta | Zawartość |
|------|-----------|-----------|
| `.env` | OAuth server, komponenty | `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `SHOP`, R2, OpenAI, Resend (Limity), SerpAPI, Gmail IMAP, Meta (opcjonalnie)… |
| `.shopify_session.json` | `shopify_client.py`, wszystkie komponenty | Token OAuth, kanoniczny `shop`: `19v3bj-n0.myshopify.com` |
| `shopify.app.toml` | Shopify CLI | Scopes, client ID |
| `Komponenty/dodajobraz/markets_config.json` | `dodajobraz`, dialog rynków | 7 rynków, markup % |

**Nie commitować:** `.env`, `.shopify_session.json`

---

## OAuth

```powershell
cd c:\Strona\pusty\cursor-api
npm run oauth
```

- Serwer: `oauth-server.mjs` (port 3000)
- Po sukcesie: `.shopify_session.json`
- Status w GicleeApp: toolbar **Stan sesji** → [`../giclee_app/docs/session-status.md`](../giclee_app/docs/session-status.md)

Wymagane scopes: patrz [`../SHOP_KNOWLEDGE.md`](../SHOP_KNOWLEDGE.md) §3.

---

## Shopify client

Centralny moduł: `Komponenty/dodajobraz/shopify_client.py`

Używany przez: `dodajobraz`, `produkcja`, `blog`, `socialmedia/cykl`, `zadania`, `mockup` (przez `create.add_follow_up_image`).

---

## R2 (Cloudflare)

Bucket: **`giclee-zoom`**

| Prefix / użycie | Komponent | Dokument |
|-----------------|-----------|----------|
| `customer-uploads/{uuid}/` | mockup-order-worker | [`worker/mockup-order-worker.md`](worker/mockup-order-worker.md) |
| Zoom reprodukcji (kafelki) | `dodajobraz/zoom_publish.py` | [`komponenty/dodajobraz.md`](komponenty/dodajobraz.md) |

Konfig R2: `.env` + `Komponenty/dodajobraz/r2_storage.py`

Public URL: `https://pub-c9a1bd43074c459d98d4cc0292b1210e.r2.dev`

---

## Zmienne `.env` — Limity, Poczta, Meta (skrót)

| Zmienna | Komponent | Uwaga |
|---------|-----------|--------|
| `R2_*`, `CLOUDFLARE_API_TOKEN` | limity, dodajobraz | Ten sam bucket `giclee-zoom` |
| `RESEND_API_KEY` | limity | **Full access** — Worker secret może być send-only |
| `SERPAPI_KEY` | limity, nazwijobraz | |
| `GMAIL_IMAP_USER`, `GMAIL_IMAP_APP_PASSWORD` | poczta | Hasło aplikacji Google |
| `META_APP_ID`, `META_APP_SECRET` | limity (kreator Meta) | Opcjonalne — long-lived auto |

Worker secrets (`RESEND_API_KEY`, `SHOPIFY_WEBHOOK_SECRET`): tylko `wrangler secret` — wartości nie da się odczytać z panelu.

---

## Kto od kogo zależy (skrót)

```
giclee_app (launcher)
    └── uruchamia Komponenty/* (subprocess / inline)

Komponenty/dodajobraz/shopify_client.py
    ├── dodajobraz, produkcja, blog, zadania, mockup (publish)
    └── wymaga .shopify_session.json

Komponenty/_shared/
    ├── auth.py          — hasło aplikacji
    ├── fx_rates.py      — NBP → dialog rynków
    ├── activity_log.py  — JSONL dziennik
    └── window_geometry.py — pozycjonowanie okien Tk

Komponenty/limity/
    ├── collectors.py    — R2, Resend, SerpAPI, Meta (import z dodajobraz + socialmedia/cykl)
    └── view.py          — inline dashboard + meta_renew_wizard

Komponenty/poczta/
    └── imap_client.py   — Gmail IMAP (odczyt + kosz)

mockup-order-worker/   — niezależny (Wrangler), współdzieli tylko R2 bucket
```

---

## Aliasy domeny Shopify

| Kontekst | Wartość |
|----------|---------|
| Kanoniczny OAuth | `19v3bj-n0.myshopify.com` |
| CLI theme push | `giclee-art-3.myshopify.com` |
| Domena publiczna | `gicleeart.eu` |

To ten sam sklep — różne aliasy w różnych narzędziach.
