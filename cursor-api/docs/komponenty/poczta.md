# Poczta firmowa

**Folder:** `Komponenty/poczta/`  
**Tryb GicleeApp:** `inline`  
**Konto:** `gicleeartpl@gmail.com` (domyślnie)

Podgląd skrzynki Gmail przez IMAP — lista wiadomości, podgląd treści, licznik nieprzeczytanych, **usuwanie do Kosza**, auto-odświeżanie co 3 min.

---

## Konfiguracja

W `cursor-api/.env`:

```env
GMAIL_IMAP_USER=gicleeartpl@gmail.com
GMAIL_IMAP_APP_PASSWORD=xxxxxxxxxxxxxxxx
CLIENT_ORDERS_DIR=E:\Firma\1. Obrazy\3. Klienci
```

1. Konto Google → Bezpieczeństwo → weryfikacja 2-etapowa (wymagana).
2. Hasła aplikacji → wygeneruj hasło dla „Poczta”.
3. Spacje w haśle aplikacji są opcjonalne (kod je usuwa).

Alternatywna nazwa zmiennej: `GMAIL_APP_PASSWORD`.

---

## Auto-pobieranie zamówień „Własna fotografia”

Po każdym odświeżeniu (co 3 min) komponent skanuje maile z **„własna fotografia”** w temacie (Worker: `Giclée — zamówienie #… — własna fotografia`).

Mail zawiera **linki do R2**, nie załączniki IMAP — program parsuje HTML i pobiera:

| Plik w folderze | Źródło |
|-----------------|--------|
| `Oryginał zdjęcia klienta.*` | link R2 |
| `Podgląd mockupu.*` | preview |
| `Dane kadrowania.json` | crop.json |
| `meta.json` | meta.json |
| `dane_klienta.txt` | dane z maila |

Przy **wielu pozycjach** „Własna fotografia” w jednym zamówieniu (Worker oddziela je linią `<hr>`) pliki dostają sufiks `_1`, `_2`, … — np. `Oryginał zdjęcia klienta_1.jpg`, `Oryginał zdjęcia klienta_2.jpg`. Pojedyncza pozycja — nazwy bez sufiksu (jak dotychczas).

Folder: `{CLIENT_ORDERS_DIR}/Numer zamówienia #1001` (bez `:` — ograniczenie Windows).

Stan: `Komponenty/poczta/data/processed_client_orders.json` — UID maila zapisany po udanym pobraniu. Jeśli folder zamówienia jest **niekompletny** (np. brakuje plików `_2` albo folder w ogóle nie powstał), Odśwież pobierze brakujące pliki mimo wpisu w JSON.

Moduł: `client_order_processor.py`

---

## Pliki

| Plik | Rola |
|------|------|
| `view.py` | UI: lista, podgląd, Odśwież, usuwanie, auto-zamówienia |
| `imap_client.py` | Połączenie IMAP, parsowanie wiadomości |
| `client_order_processor.py` | Pobieranie plików zamówień z linków R2 |
| `env_config.py` | Odczyt `.env` |
| `component.json` | Kafelek w launcherze |

---

## Resend vs IMAP

| | Resend (Worker) | Ten komponent (IMAP) |
|--|-----------------|----------------------|
| Kierunek | **Wysyłka** maili z `@gicleeart.eu` | **Odczyt** skrzynki Gmail |
| Użycie | Potwierdzenia zamówień mockup | Codzienny podgląd poczty |

Szczegóły usług: [`../../../USLUGI.md`](../../../USLUGI.md)

---

## Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| „Brak GMAIL_IMAP_APP_PASSWORD” | Dodaj hasło aplikacji w `.env`, uruchom ponownie |
| „IMAP: Login failed” | Sprawdź 2FA i hasło aplikacji (nie zwykłe hasło Gmail) |
| Pusta lista przy filtrze | Wyłącz „Tylko nieprzeczytane” |
| Podwójne logowanie | Normalne — `inbox_stats` i `fetch_inbox_messages` to osobne sesje |
