# Analiza ruchu

Hub warstwy API: [`../README.md`](../README.md)

**Komponent:** `Komponenty/analytics/` · **tryb:** inline (GicleeApp)  
**Serwer:** `python -m Komponenty.analytics.server` · domyślny port **5100**  
**Baza:** SQLite `Komponenty/analytics/dane/analytics.db`

---

## Cel

Moduł łączy **eventy ruchu ze sklepu** (Shopify Customer Events / Custom Pixel) z **danymi sprzedażowymi** (Shopify Admin API — istniejący `shopify_client.py`):

`wejście → produkt → koszyk → checkout → zakup`

---

## Uruchomienie

1. W `.env` ustaw:
   - `ANALYTICS_COLLECT_SECRET` — losowy ciąg (min. 32 znaki)
   - opcjonalnie `ANALYTICS_COLLECT_URL` — publiczny URL collect w produkcji
   - opcjonalnie `ANALYTICS_ALLOWED_SHOP_DOMAIN=gicleeart.eu`
   - opcjonalnie `ANALYTICS_AUTO_SYNC_SECONDS=300` — interwał auto-sync z chmury (0 = wyłączone)
2. GicleeApp → **Marketing → Analiza ruchu** → **Uruchom i otwórz dashboard**
3. Albo: `cd cursor-api && python -m Komponenty.analytics.server`

Dashboard: `http://127.0.0.1:5100/`

**Restart serwera:** GicleeApp → **Uruchom i otwórz dashboard** zatrzymuje stary proces w aplikacji i kończy pozostawione w tle `python -m Komponenty.analytics.server` na porcie 5100. Jeśli po aktualizacji kodu endpointy zwracają 404 (np. wykluczenia), użyj tego przycisku albo zamknij stare terminale z serwerem analityki.

---

## Pixel Shopify (Customer Events)

1. Shopify Admin → **Ustawienia → Dane klienta → Pixeli klienta → Dodaj niestandardowy**
2. Skopiuj kod z zakładki **Konfiguracja** w dashboardzie (lub plik `Komponenty/analytics/pixel/giclee-analytics-pixel.js`)
3. Ustaw w pixelu:
   - `COLLECT_URL` = publiczny adres `POST /api/analytics/collect`
   - `COLLECT_SECRET` = ten sam co `ANALYTICS_COLLECT_SECRET`
4. Zapisz pixel — **po aktualizacji kodu w projekcie wklej ponownie** (Shopify nie synchronizuje się samo)

**Sandbox Shopify:** Custom Pixel nie ma dostępu do `window.location` sklepu — pixel używa `event.context.document.location` i `fetch` (nie `sendBeacon` z JSON). Szczegóły: [Shopify — About web pixels](https://shopify.dev/docs/apps/build/marketing-analytics/pixels).

**Produkcja:** collect na **Cloudflare Worker** (ten sam co mockupy) — wdrożenie: [`../../mockup-order-worker/WDROZENIE-ANALYTICS.md`](../../mockup-order-worker/WDROZENIE-ANALYTICS.md)

---

## Chmura (Worker + D1) ↔ PC

| Warstwa | Rola |
|---------|------|
| **Worker** `POST /api/analytics/collect` | Pixel ze sklepu → D1 (24/7) |
| **Worker** `GET /api/analytics/export` | Export eventów |
| **Worker** `POST /api/analytics/purge` | Retencja D1 — usuwa eventy starsze niż N dni |
| **GicleeApp** `POST /api/analytics/pull-worker` | Sync z chmury → SQLite + **budowa sesji** (`sessions.py`) |
| **Auto-sync** | Przy otwarciu dashboardu + co **5 min** (serwer w tle). Gdy chmura ma więcej eventów niż lokalnie → **backfill** (kursor w `analytics_meta.worker_sync_cursor`, nie `MAX(created_at)`) |
| Dashboard | KPI z lokalnej bazy po sync; pasek statusu pixel/sync/chmura vs lokalnie |

---

## Endpointy API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| POST | `/api/analytics/collect` | Eventy z pixela (nagłówek `X-Analytics-Secret`) |
| GET | `/api/analytics/overview` | KPI + timeline (unikalni/dzień) |
| GET | `/api/analytics/countries` | Ruch według krajów |
| GET | `/api/analytics/funnel` | Lejek zakupowy + porównanie z poprzednim okresem |
| GET | `/api/analytics/products` | Produkty — unikalni, śr. unikalni/dzień, delta vs poprzedni okres |
| GET | `/api/analytics/sources` | Źródła + UTM |
| GET | `/api/analytics/frame-funnel` | Lejek konfiguratora ram (`giclee_app:*`) |
| GET | `/api/analytics/realtime` | Aktywni użytkownicy |
| GET | `/api/analytics/sessions` | Sesje / timeline (budowane przy sync) |
| GET | `/api/analytics/insights` | Insighty (działają od małej próbki danych) |
| GET | `/api/analytics/status` | Pixel, sync, chmura vs lokalnie |
| GET | `/api/analytics/settings` | Wykluczenia, szablony UTM |
| POST | `/api/analytics/settings` | Zapis ustawień / dodaj wykluczenie visitor/IP |
| GET | `/api/analytics/utm-preview` | Podgląd linku UTM |
| GET | `/api/analytics/export?format=csv` | Eksport eventów |
| GET | `/api/analytics/export?format=weekly_report&download=1` | Raport tygodniowy (txt) |
| POST | `/api/analytics/rebuild-sessions` | Przebudowa sesji z eventów |
| POST | `/api/analytics/purge-worker?days=90` | Retencja D1 w chmurze |
| DELETE | `/api/analytics/delete` | RODO — usuwanie po session/visitor/dates |
| POST | `/api/analytics/sync-shopify` | Sync zamówień → checkout_completed |
| POST | `/api/analytics/pull-worker` | Sync z chmury (D1 → SQLite) |
| POST | `/api/analytics/test-event` | Event testowy (localhost) |

**Filtry segmentów** (query): `country`, `device` (mobile/desktop/tablet), `source` (direct/organic_search/paid/…), `preset` (7d/30d/…).

---

## Dashboard — zakładki

| Zakładka | Zawartość |
|----------|-----------|
| Podsumowanie | KPI + wykres unikalni/dzień |
| Lejek / Produkty | Strzałki ↑↓ vs poprzedni okres |
| Ścieżki | Sesje z landing → produkty → koszyk |
| Konfigurator ram | Lejek `giclee_app:frame_*` |
| Konfiguracja | Wyklucz swój ruch, generator UTM, retencja D1 |

---

## Wykluczenie własnego ruchu

Konfiguracja → **Pomiń mój ruch** lub suwak **Wyklucz moje IP** na pasku górnym (auto-wykrywa publiczne IP przez ipify). Lista wykluczeń z przyciskiem **Usuń**. Na pasku głównym dashboardu suwak **Wykluczenia** włącza/wyłącza filtrowanie KPI (bez usuwania listy).

Hash IP/visitor musi być zgodny z Workerem — ta sama sól `ANALYTICS_HASH_SALT` (domyślnie `giclee-analytics` w `wrangler.toml` i lokalnie). Po aktualizacji soli usuń stare wpisy IP i dodaj ponownie.

**Ważne:** eventy zebrane **przed** wdrożeniem `ip_hash` na Workerze **nie mają IP w bazie** — sam suwak IP ich nie ukryje. Wtedy dashboard automatycznie (przy włączeniu suwaka) wyklucza też **visitor ID** z częstych sesji testowych (≥2 eventy). Ręcznie: lista **Ostatni visitorzy** → **Wyklucz**. Pasek statusu: `Wykluczenia: −N eventów` lub `0 eventów z IP w bazie`.

Nowe eventy z wykluczonego visitor/IP są pomijane przy collect i sync; agregacje filtrują historyczne po `visitor_id_hash` i `ip_hash` (kolumna + metadata).

---

## Osobny Worker analityki

Przy obecnym ruchu **zostaw na jednym Workerze** (mockup + analityka). Rozdzielenie ma sens dopiero przy **>~10k eventów/dzień** (izolacja deployów) — na planie Free limit requestów jest **wspólny dla konta**, osobny Worker nie zwiększa puli.

---

## RODO

- Brak pełnego IP w bazie
- `visitor_id` / `customer_id` — hash SHA-256 z solą
- Kraj z pixela / nagłówków edge (`CF-IPCountry`), inaczej `unknown`
- Event bez zgody (`consent_status=denied`) — pomijany
- `DELETE /api/analytics/delete?session_id=…` lub `visitor_id_hash=…`

---

## Sync Shopify

Przycisk **Sync Shopify** w dashboardzie (lub `POST /api/analytics/sync-shopify`) pobiera opłacone zamówienia przez istniejący klient OAuth i:

- uzupełnia brakujące `checkout_completed` (oznaczone `match_type: estimated` w metadata)
- zapisuje atrybucję w `analytics_attribution`

Wymaga sesji `.shopify_session.json` i scope **`read_orders`** w OAuth (`SCOPES` w `.env` jak w `shopify.app.toml`, potem `npm run oauth`). Przy braku scope API zwraca czytelny błąd zamiast cichego 0.

---

## Testy

```powershell
cd cursor-api
python -m pytest tests/test_analytics.py -v
```

---

## Pliki

| Plik | Rola |
|------|------|
| `view.py` | Launcher inline w GicleeApp |
| `server.py` | HTTP API + statyczny dashboard |
| `collect.py` | Walidacja i zapis eventów |
| `sessions.py` | Budowa sesji (collect + sync) |
| `settings.py` | Wykluczenia, UTM, meta sync |
| `worker_sync.py` | Import D1 → SQLite |
| `aggregations.py` | KPI, lejek, kraje, insighty |
| `storage.py` | SQLite |
| `shopify_sync.py` | Zamówienia Shopify |
| `pixel/giclee-analytics-pixel.js` | Custom Pixel |
| `web/` | Dashboard HTML/JS/CSS (Chart.js) |

---

## Weryfikacja eventów

1. Dashboard → **Wyślij event testowy** — licznik eventów rośnie
2. `GET /api/analytics/health` → `total_events`
3. Po wdrożeniu pixela: wejdź na sklep → sprawdź **Realtime** w dashboardzie
