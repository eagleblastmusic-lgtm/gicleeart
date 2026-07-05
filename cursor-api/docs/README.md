# cursor-api — dokumentacja warstwy API

Hub integracyjny (3 warstwy): [`../../docs/README.md`](../../docs/README.md)  
Mapa zależności: [`../../docs/zaleznosci.md`](../../docs/zaleznosci.md)

Folder kodu: `cursor-api/` — Worker Cloudflare, OAuth Shopify, komponenty Python w `Komponenty/`.

---

## Drzewo dokumentacji (warstwa API)

```
cursor-api/docs/
├── README.md                    ← jesteś tutaj
├── zaleznosci-wewnetrzne.md     OAuth, .env, R2, shopify_client
├── shared.md                    Komponenty/_shared
├── troubleshooting.md
├── worker/
│   ├── README.md
│   └── mockup-order-worker.md
└── komponenty/
    ├── README.md
    ├── dodajobraz.md
    ├── produkcja.md
    ├── mockup-katalogowy.md
    └── …
```

---

## Archiwum (tylko czytanie)

[`../SHOP_KNOWLEDGE.md`](../SHOP_KNOWLEDGE.md) (~1400 linii) — historia: rynki, tagi, prompty LLM. **Nie aktualizuj.**  
Nowe zmiany → plik w [`komponenty/`](komponenty/). Czytaj sekcję SHOP tylko gdy brakuje w pliku modułowym.

---

## Szybka mapa: temat → plik

| Chcę… | Czytaj |
|-------|--------|
| Worker upload + mail po zakupie | [`worker/mockup-order-worker.md`](worker/mockup-order-worker.md) |
| Dodać reprodukcję do sklepu | [`komponenty/dodajobraz.md`](komponenty/dodajobraz.md) |
| Mockup ramki na zdjęciu katalogowym | [`komponenty/mockup-katalogowy.md`](komponenty/mockup-katalogowy.md) |
| Zamówienia / produkcja | [`komponenty/produkcja.md`](komponenty/produkcja.md) |
| Limity usług (R2, Resend, Meta…) | [`komponenty/limity.md`](komponenty/limity.md) |
| Poczta Gmail (IMAP) | [`komponenty/poczta.md`](komponenty/poczta.md) |
| Odnowa tokenów Meta | [`komponenty/meta-tokeny.md`](komponenty/meta-tokeny.md) |
| OAuth, sesja, R2 | [`zaleznosci-wewnetrzne.md`](zaleznosci-wewnetrzne.md) |
| Moduły współdzielone (_shared) | [`shared.md`](shared.md) |
| Uruchomić launcher GUI | [`../giclee_app/docs/README.md`](../giclee_app/docs/README.md) |
| Integracja Custom GPT (lustro GitHub, nagrania) | [`komponenty/integracjagpt.md`](komponenty/integracjagpt.md) |
| Coś nie działa | [`troubleshooting.md`](troubleshooting.md) |

---

## Konfiguracja

| Plik | Zawartość |
|------|-----------|
| `.env` | Shopify API, R2, OpenAI… (nie commitować) |
| `.shopify_session.json` | Token OAuth po `npm run oauth` |
| `CHECKLIST_SETUP.md` | Pierwsze uruchomienie |
| `SECURITY.md` | Sekrety, dobre praktyki |

---

## Uruchomienie komponentów

Komponenty uruchamia się przez **GicleeApp** (`python -m giclee_app`) — patrz [`../giclee_app/docs/README.md`](../giclee_app/docs/README.md).

OAuth: kanoniczny shop `19v3bj-n0.myshopify.com`, alias CLI `giclee-art-3.myshopify.com`.

---

## Ostatnia aktualizacja

2026-06-04 — utworzenie warstwy `cursor-api/docs/`.
