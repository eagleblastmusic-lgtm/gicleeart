# USŁUGI — mapa kont i subskrypcji zewnętrznych

> **Jeden plik** — co gdzie płacisz, po co to jest, jakie ma limity.  
> Korzeń repo `pusty/`. Powiązane: [`MATKA.md`](MATKA.md) · [`docs/zaleznosci.md`](docs/zaleznosci.md)

**Aktualizuj ten plik** po każdej zmianie planu, nowej usłudze lub odkryciu zbędnej płatności (np. duplikat poczty w OVH).

---

## Szybka mapa (co do czego)

| Usługa | Po co w GicleeArt | Panel logowania | Plan / subskrypcja | Uwagi |
|--------|------------------|-----------------|-------------------|--------|
| **Shopify** | Sklep, checkout, zamówienia, Markets | [admin.shopify.com](https://admin.shopify.com) | **Standardowy** | Hosting sklepu — nie OVH |
| **OVH** | Domena `gicleeart.eu`, DNS (Shopify, Resend, R2…) | [ovh.com](https://www.ovh.com) → Web Cloud | Domena + strefa DNS + **sprawdź pocztę** | Patrz sekcja OVH |
| **Cloudflare** | Worker upload, R2 (zoom + zdjęcia klientów) | [dash.cloudflare.com](https://dash.cloudflare.com) | Konto **eagleblastmusic** — **uzupełnij plan** | Worker ≠ hosting OVH |
| **Resend** | Maile po opłaceniu zamówieniu (mockup) | [resend.com](https://resend.com) | Darmowy start — **uzupełnij limit** | Wysyłka, nie skrzynka |
| **Shopify Partners** | Aplikacja OAuth „Cursor API” (GicleeApp) | [partners.shopify.com](https://partners.shopify.com) | Partners (dev) | Wersja app: `cursor-api-9` |
| **Google Gmail** | Odbiór powiadomień sklepu | gicleeartpl@gmail.com | Bezpłatny | Docelowy odbiorca maili z Workera |
| **SerpAPI** | Nazwij obraz — Google Lens | [serpapi.com](https://serpapi.com) | Free: **100 zapytań/mc** | Klucz w `cursor-api/.env` |
| **Meta (Facebook/IG)** | Cykl postów (socialmedia/cykl) | [developers.facebook.com](https://developers.facebook.com) | Bezpłatne API — limity Graph | Tokeny w komponencie, TTL ~60 dni |
| **NBP API** | Kursy walut w dialogu rynków | [api.nbp.pl](https://api.nbp.pl) | **Darmowe**, bez klucza | Cache 24h lokalnie |
| **Vercel** | Kalkulator GicleeLab (iframe w motywie) | [vercel.com](https://vercel.com) | **uzupełnij plan** | `kalkulator1-henna.vercel.app` |
| **jsDelivr** | CDN OpenSeadragon (zoom) | — | Darmowy CDN | W snippecie motywu |
| **0x0.st / catbox.moe** | Tymczasowy hosting obrazu (Nazwij obraz) | — | Darmowe, publiczne | Nie dla plików poufnych |

---

## OVH — domena i DNS (nie zastępuje Shopify ani Cloudflare)

**Rola:** `gicleeart.eu` + rekordy DNS kierujące ruch (sklep, mail Resend, ewentualnie subdomeny).

### Co jest potrzebne

| Usługa OVH | Potrzebna? | Po co |
|------------|------------|--------|
| **Nazwy domen** (`gicleeart.eu`) | **Tak** | Właściciel domeny, odnowienie roczne |
| **Strefy DNS** | **Tak** | Rekordy A/CNAME → Shopify, TXT/CNAME/MX → Resend, itd. |
| **Email Pro** / **Zimbra** | **Sprawdź** | Tylko jeśli **czytasz** pocztę na `@gicleeart.eu`. Do maili z mockupu (Worker → Resend → Gmail) **nie jest wymagane** |

### Czego w OVH **nie** potrzebujesz przy obecnym setupie

| Usługa OVH | Dlaczego nie |
|------------|--------------|
| **Hosting** / **Managed WordPress** | Sklep jest na **Shopify** |
| **Web Cloud Databases** | Baza = Shopify + pliki w **R2** |
| **OVH jako API uploadu** | Upload klienta = **Cloudflare Worker + R2** |

### OVH vs Cloudflare Worker + R2

| | Cloudflare Worker + R2 | OVH Web Cloud |
|--|------------------------|---------------|
| Upload zdjęć, webhook, mail | **Tak — używamy** | Trzeba by własny serwer/VPS |
| Zoom HD reprodukcji | **R2** bucket `giclee-zoom` | — |
| Domena + DNS | Rekordy **w OVH** wskazują na Shopify/Resend/CF | **Tak — domena u OVH** |

### Rekordy DNS (Resend) — koszt

Dodanie TXT / MX / CNAME w strefie DNS OVH = **0 zł** (część domeny). Płacisz tylko za odnowienie domeny (i ewentualnie zbędną pocztę OVH).

### Do uzupełnienia przez Ciebie

```
[ ] Roczna opłata za gicleeart.eu: _______ PLN/EUR
[ ] Email Pro — aktywny? tak / nie — jeśli nie używasz → rozważ rezygnację
[ ] Zimbra — aktywny? tak / nie — duplikat poczty? → rozważ rezygnację
[ ] Data odnowienia domeny: __.__.____
```

---

## Cloudflare

**Konto (Worker URL):** `eagleblastmusic.workers.dev`  
**Panel:** [dash.cloudflare.com](https://dash.cloudflare.com)

### Co używamy

| Produkt | Nazwa / binding | Po co |
|---------|-----------------|--------|
| **Worker** | `giclee-mockup-orders` | Upload mockupu, webhook Shopify, Resend |
| **R2** | bucket `giclee-zoom` | Zoom HD reprodukcji + `customer-uploads/` (zdjęcia klientów) |
| **Public R2** | `pub-c9a1bd43074c459d98d4cc0292b1210e.r2.dev` | Linki w mailu / zoom (sprawdź 403) |

### Limity (orientacyjnie — plan Free)

| Zasób | Typowy limit Free | U nas |
|-------|-------------------|--------|
| Worker requests | ~100 000 / dobę | Upload + webhooky zamówień |
| R2 storage | 10 GB / mc | App śledzi w `dodajobraz` (`R2_STORAGE_QUOTA_GB=10`) |
| R2 Class A (zapis) | 1 000 000 / mc | Upload kafelków zoom |
| R2 Class B (odczyt) | 10 000 000 / mc | Podgląd zoom na stronie |
| Egress R2 → internet | **Bez opłat** u CF | — |

Opcjonalnie w `.env`: `CLOUDFLARE_API_TOKEN` — metryki operacji A/B w GUI dodajobraz.

**GUI:** komponent **Dodaj obraz** → przycisk **Cloudflare** — okno z paskami zużycia (magazyn, Class A/B, egress) i podziałem `zoom/` vs `customer-uploads/`.  
**GicleeApp:** kafelek **Limity** — ten sam R2 + Resend + SerpAPI + inne usługi na jednym ekranie.

### Worker — limity aplikacyjne

| Limit | Wartość |
|-------|---------|
| Max rozmiar pliku upload | **50 MB** (Worker) |
| Sekrety | `RESEND_API_KEY`, `SHOPIFY_WEBHOOK_SECRET` |

### Do uzupełnienia

```
[ ] Plan Cloudflare: Free / Paid _______
[ ] Miesięczny koszt (jeśli Paid): _______
```

---

## Shopify

| Element | Wartość |
|---------|---------|
| Plan | **Standardowy** |
| Sklep (publiczny) | `gicleeart.eu` |
| CLI / theme push | `giclee-art-3.myshopify.com` |
| OAuth kanoniczny | `19v3bj-n0.myshopify.com` |
| Motyw live | `#197314249052` (Kopia Giclee Art Br) |
| Aplikacja dev | **Cursor API** (`shopify.app.toml`, Partners `cursor-api-9`) |

**Rola:** cały sklep, płatności, Markets (7 rynków), webhooki do Workera.

### Do uzupełnienia

```
[ ] Abonament Shopify: _______ / mc
[ ] Opłaty transakcyjne: _______% (+ Shopify Payments / inna bramka)
```

---

## Resend (wysyłka maili transakcyjnych)

**Rola:** Worker wysyła mail po `orders/paid` z linkami do R2. Kafelek **Limity** w GicleeApp **odczytuje** zużycie (osobny klucz API w `.env`).

| Element | Wartość |
|---------|---------|
| Domena wysyłki | `gicleeart.eu` (po weryfikacji DNS w OVH) |
| From PL | `zamowienia@gicleeart.eu` |
| From intl | `orders@gicleeart.eu` |
| Odbiorca (merchant) | `gicleeartpl@gmail.com` |
| **Enable Receiving** | **OFF** — nie odbieramy poczty w Resend |

### Dwa klucze API (Worker vs Limity)

| Miejsce | Uprawnienia | Po co |
|---------|-------------|--------|
| `wrangler secret put RESEND_API_KEY` | **Sending access** (send-only) wystarczy | Worker wysyła mail po webhooku |
| `cursor-api/.env` → `RESEND_API_KEY` | **Full access** zalecany | Limity: paginacja GET `/emails`, licznik wysłanych w mc |

Send-only w `.env` daje HTTP **401 restricted_api_key** w Limity — Worker nadal może wysyłać.

### Limity — jak liczy maile

- API GET `/emails` **nie zwraca** nagłówków `x-resend-monthly-quota` w odpowiedzi listy.
- Limity liczy wysłane maile **paginacją listy** (`collectors.py`), nie z nagłówków HTTP.
- Requesty Python wymagają nagłówka **User-Agent** (bez niego Resend zwraca **403**).

Opcjonalnie w `.env`: `RESEND_MONTHLY_QUOTA=3000`, `RESEND_DAILY_QUOTA=100` (progi w UI).

### Resend vs poczta OVH

| | Resend + DNS (OVH) | Email w OVH (Email Pro / Zimbra) |
|--|-------------------|----------------------------------|
| Wysyłka „z @gicleeart.eu” | **Tak** (API) | Tak (klient pocztowy) |
| Skrzynka do czytania | **Nie** — czytasz na Gmail | **Tak** |
| Maile z mockupu / Worker | **Tak — to używamy** | Nie potrzebne do tego flow |

### Limity (plan darmowy — typowo)

| Limit | Wartość orientacyjna |
|-------|---------------------|
| Maile / mc | ~3 000 (sprawdź w panelu Resend) |
| Domeny | 1+ po weryfikacji |

Stary tryb testowy `onboarding@resend.dev` — wysyłka **tylko** na adres konta Resend (blokada innych Gmaili).

### Gmail IMAP (odczyt skrzynki w GicleeApp)

**Rola:** Kafelek **Poczta firmowa** — podgląd wiadomości na `gicleeartpl@gmail.com` (nie wysyłka).

| Element | Wartość |
|---------|---------|
| Konto | `gicleeartpl@gmail.com` |
| Protokół | IMAP `imap.gmail.com:993` |
| Auth | Hasło aplikacji Google (2FA wymagane) |
| Zmienne `.env` | `GMAIL_IMAP_USER`, `GMAIL_IMAP_APP_PASSWORD` |
| Komponent | `Komponenty/poczta/` (tryb inline) |

Maile **wysyłane** z domeny sklepu nadal idą przez **Resend** — IMAP służy tylko do czytania skrzynki Gmail.

### Do uzupełnienia

```
[ ] Konto Resend (email logowania): ________________
[ ] Plan: Free / Pro _______
[ ] Maile w tym mc (panel Resend): _______
```

---

## SerwAPI, Meta, NBP, Vercel

### SerpAPI (`SERPAPI_KEY` w `.env`)

- **Komponent:** `nazwijobraz` (Google Lens, wyszukiwanie)
- **Free:** 100 zapytań / miesiąc
- Po przekroczeniu: płatny plan lub pominięcie Lens (działa 7 innych źródeł)

### Meta Graph API (`socialmedia/cykl`)

- **Komponent:** automatyczne posty FB/IG (4 kanały: FB PL/EN, IG PL/EN)
- **Koszt API:** darmowy tier; limity ~200 calls/h na app
- **Tokeny:** plik `Komponenty/socialmedia/data/cykl/meta_credentials.json` (gitignore)
- **Status w GUI:** kafelek **Limity** → sekcja Meta (dni do wygaśnięcia, `debug_token`)
- **Odnowa:** Limity → **Odnów tokeny** — kreator 5 kroków; **jeden** user token → Page tokeny → zapis **4 kanałów naraz**
- **Opcjonalnie `.env`:** `META_APP_ID`, `META_APP_SECRET` — auto wymiana long-lived w kreatorze
- Page tokeny często **bez daty wygaśnięcia** w API — Limity pokazuje «bez daty (OK)»; to normalne
- Publikacja pełna wymaga Facebook App Review — cykl może być półautomatyczny

Docs: [`cursor-api/docs/komponenty/meta-tokeny.md`](cursor-api/docs/komponenty/meta-tokeny.md)

### NBP API

- Kursy PLN/EUR w `dodajobraz` → dialog **Rynki…**
- Darmowe, cache 24h

### Vercel

- **URL:** `https://kalkulator1-henna.vercel.app/`
- **Rola:** iframe kalkulatora PPI (strona fotografia-obraz); logika skopiowana do `lib/giclee-print-analysis/`
- Osobny projekt — **nie** ten repo Shopify

---

## Maile — kto co wysyła (żeby się nie pogubić)

```
Klient kupuje własną fotografię
  → Shopify webhook
  → Cloudflare Worker
  → Resend (From: @gicleeart.eu)
  → Gmail: gicleeartpl@gmail.com

Skrzynka biuro@ / kontakt@ @gicleeart.eu (jeśli masz)
  → OVH Email / Zimbra (osobna usługa, osobna opłata)
```

---

## Checklist: zbędne koszty do przeglądu co kwartał

- [ ] OVH: **Email Pro** i **Zimbra** — oba potrzebne, czy jeden wystarczy?
- [ ] OVH: hosting / baza — czy przypadkiem aktywne mimo Shopify?
- [ ] Resend: czy nadal w limicie Free?
- [ ] Cloudflare R2: zużycie vs 10 GB (panel dodajobraz / CF dashboard)
- [ ] SerpAPI: licznik zapytań w miesiącu
- [ ] Shopify: czy plan Standard nadal optymalny
- [ ] Vercel: czy kalkulator nadal używany (iframe w motywie)

---

## Instrukcja dla AI

Po zmianie planu, konta lub integracji **zaktualizuj ten plik** (tabela + sekcja usługi).  
Nie wpisuj haseł ani pełnych kluczy API — tylko *gdzie* leżą (`cursor-api/.env`, `wrangler secret`).

Powiązana dokumentacja techniczna:

- Worker + Resend: `cursor-api/mockup-order-worker/WDROZENIE.md`
- R2: `cursor-api/docs/zaleznosci-wewnetrzne.md`
- Env: `cursor-api/Komponenty/notatnik/notatki/04-konfiguracja-env.md`
