# Troubleshooting — cursor-api (warstwa API)

Hub: [`README.md`](README.md)  
Macierz cross-warstwowa: [`../../docs/zaleznosci.md`](../../docs/zaleznosci.md)

---

## OAuth / Shopify API

| Objaw | Sprawdź |
|-------|---------|
| 401 Unauthorized | `.shopify_session.json` — uruchom `npm run oauth` |
| Brak scope | `shopify.app.toml` vs wymagane scopes w SHOP_KNOWLEDGE §3 |
| Zły shop w sesji | Kanoniczny: `19v3bj-n0.myshopify.com` |

→ [`zaleznosci-wewnetrzne.md`](zaleznosci-wewnetrzne.md)

---

## Worker (mockup-order-worker)

| Objaw | Sprawdź |
|-------|---------|
| Brak maila | Webhook `orders/paid`, `_Upload ID`, `SHOPIFY_WEBHOOK_SECRET` |
| CORS | `ALLOWED_ORIGINS` w `wrangler.toml` |
| 413 | Plik > 50 MB |
| 502 przy webhook | Resend API / domena `gicleeart.eu` |

→ [`worker/mockup-order-worker.md`](worker/mockup-order-worker.md) · `npx wrangler tail`

---

## R2

| Objaw | Sprawdź |
|-------|---------|
| 403 na public URL | R2 public access, `PUBLIC_BASE_URL` |
| Zoom bez kafelków | `dodajobraz/zoom_publish.py`, manifest w metafield |

---

## Komponenty Python

| Objaw | Sprawdź |
|-------|---------|
| Import error | `pip install -r requirements.txt` (+ per komponent) |
| Batch fail mid-queue | Logi w `cursor-api/logs/` |
| Zoom nie na stronie | [`komponenty/dodajobraz.md`](komponenty/dodajobraz.md) |

Notatki FAQ: `Komponenty/notatnik/notatki/05-faq-i-trobleshoot.md`

---

## Limity (`Komponenty/limity/`)

| Objaw | Sprawdź |
|-------|---------|
| Resend HTTP 403 | `collectors.py` — nagłówek `User-Agent`; zrestartuj GicleeApp |
| Resend HTTP 401 restricted | Klucz send-only — w `.env` **Full access** (Worker secret osobno) |
| Brak licznika Resend | Paginacja `/emails`; Full access; opcjonalnie `RESEND_MONTHLY_QUOTA` |
| Meta wygasłe | **Odnów tokeny** w UI → [`komponenty/meta-tokeny.md`](komponenty/meta-tokeny.md) |
| R2 / Class A/B | `R2_*`, opcjonalnie `CLOUDFLARE_API_TOKEN` — jak w dodajobraz |

→ [`komponenty/limity.md`](komponenty/limity.md) · [`../../USLUGI.md`](../../USLUGI.md)

---

## Poczta (`Komponenty/poczta/`)

| Objaw | Sprawdź |
|-------|---------|
| Brak `GMAIL_IMAP_APP_PASSWORD` | Hasło aplikacji w `.env` |
| IMAP login failed | 2FA + hasło aplikacji (16 znaków), nie hasło konta |
| Usuwanie nie działa | COPY do `[Gmail]/Trash` + EXPUNGE — sprawdź uprawnienia IMAP |

→ [`komponenty/poczta.md`](komponenty/poczta.md)

---

## Motyw / front (objawy w przeglądarce)

→ [`../../docs/motyw/troubleshooting.md`](../../docs/motyw/troubleshooting.md)

---

## Theme dev (GicleeApp / Shopify CLI)

| Objaw | Sprawdź |
|-------|---------|
| `ETIMEDOUT` do `giclee-art-3.myshopify.com` | Firewall Windows — zezwól `node.exe` (skrypt poniżej); VPN/proxy; ponów Theme dev (GicleeApp ma retry) |
| Port 9292 zajęty / brak HTTP | GicleeApp → **Zamknij porty** lub restart Theme dev |
| Formularz hasła sklepu | Integracja z GPT → Hasło sklepu, albo `.shopify-store-password.local` w korzeniu motywu |

**Firewall Node.js (Windows, jako administrator):**

```powershell
cd C:\Strona\pusty\cursor-api\scripts
.\setup-node-firewall.ps1
```

Skrypt: `cursor-api/scripts/setup-node-firewall.ps1` — reguły wychodzące (Shopify HTTPS) i przychodzące (podgląd `:9292`).
