# Wdrożenie: zdjęcia z mockupu → R2 → mail z linkami

> **Hub dokumentacji:** [`../../docs/README.md`](../../docs/README.md)  
> **Szczegóły techniczne:** [`../docs/worker/mockup-order-worker.md`](../docs/worker/mockup-order-worker.md)

Powiadomienia trafiają na **gicleeartpl@gmail.com**.

To jest mały program w chmurze Cloudflare (Worker) — **nie wymaga włączonego komputera**.

---

## Krok 1 — konto Resend (maile)

1. Wejdź na [resend.com](https://resend.com) i załóż konto **na adresie gicleeartpl@gmail.com** (albo zweryfikuj własną domenę — patrz niżej).
2. W panelu skopiuj **API Key** (zaczyna się od `re_`).
3. Na start możesz wysyłać z `onboarding@resend.dev` (w `wrangler.toml`), **ale** wtedy Resend pozwala wysłać **tylko na ten sam e-mail, na który założyłeś konto Resend** — nie na dowolny Gmail.

**Jeśli konto Resend masz na innym mailu (np. eagleblastmusic@gmail.com):** maile na `gicleeartpl@gmail.com` **nie dojdą**. Rozwiązania:

- **A)** Nowe konto Resend zalogowane na **gicleeartpl@gmail.com** → nowy API key → `npx wrangler secret put RESEND_API_KEY`
- **B)** W Resend → **Domains** → dodaj i zweryfikuj **gicleeart.eu** → w `wrangler.toml` ustaw np. `RESEND_FROM = "Giclee Art <zamowienia@gicleeart.eu>"` → `npm run deploy`

Test (po dodaniu `RESEND_API_KEY` do `cursor-api/.env`):

```powershell
python scripts/test_resend.py
```

---

## Krok 2 — deploy Workera

W terminalu (PowerShell):

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
npm install
npx wrangler login
npx wrangler secret put RESEND_API_KEY
npx wrangler secret put SHOPIFY_WEBHOOK_SECRET
npm run deploy
```

Po `deploy` zobaczysz adres, np.:

`https://giclee-mockup-orders.twoje-konto.workers.dev`

**Skopiuj ten adres** — będzie potrzebny w motywie.

Sekret `SHOPIFY_WEBHOOK_SECRET` ustawisz w kroku 4 (po rejestracji webhooka).

---

## Krok 3 — URL w motywie Shopify

1. Shopify Admin → **Sklep online → Motywy → Dostosuj**.
2. **Ustawienia motywu** (ikona koła zębatego) → sekcja **„Mockup — własna fotografia”**.
3. Wklej adres Workera + `/api/mockup-upload`, np.:

   `https://giclee-mockup-orders.twoje-konto.workers.dev/api/mockup-upload`

4. Zapisz i opublikuj motyw.

---

## Krok 4 — webhook Shopify

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
python scripts/register_webhook.py https://giclee-mockup-orders.twoje-konto.workers.dev
```

Następnie ustaw **ten sam** signing secret w Workerze:

```powershell
npx wrangler secret put SHOPIFY_WEBHOOK_SECRET
```

(W Shopify Admin → Ustawienia → Powiadomienia → Webhooki możesz też podejrzeć / utworzyć ręcznie topic **Order payment**.)

---

## Krok 5 — push motywu na sklep

```powershell
cd c:\Strona\pusty
shopify theme push --store giclee-art-3.myshopify.com
```

(lub tylko zmienione pliki, jeśli używasz dev theme)

---

## Jak to działa po wdrożeniu

1. Klient wgrywa zdjęcie w mockupie i klika **Dodaj do koszyka**.
   - Front (motyw): scroll na górę strony → panel koszyka → upload i `POST /cart/add.js` w tle — [`../../docs/motyw/mockup-wlasna-fotografia.md`](../../docs/motyw/mockup-wlasna-fotografia.md).
2. Pliki trafiają do R2 (`customer-uploads/{uuid}/`).
3. W zamówieniu zapisuje się **Upload ID**.
4. Po opłaceniu Shopify woła Workera → mail na **gicleeartpl@gmail.com** z:
   - **numerem zamówienia** (np. #1042),
   - **ramką** (drewno, kolor, rozmiar, orientacja),
   - linkami: oryginał, podgląd mockupu, JSON kadrowania.

---

## Test

1. Otwórz stronę produktu własnej fotografii, wgraj zdjęcie, dodaj do koszyka.
2. W Shopify Admin → **Zamówienia** → otwórz testowe → w pozycji powinno być `_Upload ID`.
3. Po opłaceniu (test payment) sprawdź skrzynkę gicleeartpl@gmail.com.

Health check Workera: `GET https://…workers.dev/health`

---

## RODO

Zdjęcia klientów to dane osobowe — warto dodać informację w polityce prywatności i okresowo czyścić stary prefix `customer-uploads/` w R2.
