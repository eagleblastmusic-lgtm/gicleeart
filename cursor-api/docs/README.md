# cursor-api — dokumentacja warstwy API

Hub integracyjny (3 warstwy): [`../../docs/README.md`](../../docs/README.md)  
Mapa zależności: [`../../docs/zaleznosci.md`](../../docs/zaleznosci.md)

Folder kodu: `cursor-api/` — Worker Cloudflare, OAuth Shopify, komponenty Python w `Komponenty/`.

---

## Status architektury

Stabilizacja RC1, izolacja profili Studio i bezpieczny refaktor repozytorium są zakończone.

Kanoniczne podsumowanie zakresu, dowodów i świadomie odłożonych prac:

[`GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md`](GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md)

---

## Drzewo dokumentacji (warstwa API)

```text
cursor-api/docs/
├── README.md                                  ← jesteś tutaj
├── GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md
├── GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md   mapa wzorców GicleeApp
├── versioning.md                              jedno źródło wersji desktop
├── tracked-large-files.md                     guard historii Git
├── theme-liquid-inline-overrides.md           conditional CSS motywu
├── theme-liquid-runtime.md                    runtime motywu wg domen
├── zaleznosci-wewnetrzne.md                   OAuth, .env, R2, shopify_client
├── shared.md                                  Komponenty/_shared
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
| Sprawdzić stan zakończonego refaktoru | [`GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md`](GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md) |
| Worker upload + mail po zakupie | [`worker/mockup-order-worker.md`](worker/mockup-order-worker.md) |
| Dodać reprodukcję do sklepu | [`komponenty/dodajobraz.md`](komponenty/dodajobraz.md) |
| Mockup ramki na zdjęciu katalogowym | [`komponenty/mockup-katalogowy.md`](komponenty/mockup-katalogowy.md) |
| Zamówienia / produkcja | [`komponenty/produkcja.md`](komponenty/produkcja.md) |
| Limity usług (R2, Resend, Meta…) | [`komponenty/limity.md`](komponenty/limity.md) |
| Poczta Gmail (IMAP) | [`komponenty/poczta.md`](komponenty/poczta.md) |
| Odnowa tokenów Meta | [`komponenty/meta-tokeny.md`](komponenty/meta-tokeny.md) |
| OAuth, sesja, R2 | [`zaleznosci-wewnetrzne.md`](zaleznosci-wewnetrzne.md) |
| Moduły współdzielone (`_shared`) | [`shared.md`](shared.md) |
| Nowy komponent / helper — co już istnieje | [`GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`](GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md) |
| Profile aplikacji i kanały komponentów | [`../giclee_app/docs/component-channels.md`](../giclee_app/docs/component-channels.md), [`../giclee_app/docs/studio-production-profile.md`](../giclee_app/docs/studio-production-profile.md) |
| Zmienić wersję aplikacji | [`versioning.md`](versioning.md) |
| Zrozumieć strukturę runtime motywu | [`theme-liquid-runtime.md`](theme-liquid-runtime.md) |
| Uruchomić launcher GUI | [`../giclee_app/docs/README.md`](../giclee_app/docs/README.md) |
| Integracja Custom GPT (lustro GitHub, nagrania) | [`komponenty/integracjagpt.md`](komponenty/integracjagpt.md) |
| Coś nie działa | [`troubleshooting.md`](troubleshooting.md) |

---

## Konfiguracja i bezpieczeństwo

| Plik | Zawartość |
|------|-----------|
| `.env` | Lokalne sekrety Shopify, R2, OpenAI itd. — nigdy nie commitować |
| `.shopify_session.json` | Lokalny token OAuth po `npm run oauth` — ignorowany przez Git, nigdy nie publikować |
| `CHECKLIST_SETUP.md` | Pierwsze uruchomienie |
| [`../../SECURITY.md`](../../SECURITY.md) | Raportowanie podatności, sekrety, rotacja i granice automatyzacji |

---

## Uruchomienie aplikacji

Z katalogu `cursor-api`:

```text
python -m giclee_app                  # klasyczny GicleeApp
python -m giclee_app.studio_preview   # Giclée Studio Preview
python -m giclee_app.studio           # produkcyjne Giclée Studio
```

Szczegóły: [`../giclee_app/docs/README.md`](../giclee_app/docs/README.md).

OAuth: kanoniczny shop `19v3bj-n0.myshopify.com`, alias CLI `giclee-art-3.myshopify.com`.

---

## Ostatnia aktualizacja

2026-07-16 — zamknięcie stabilizacji RC1, izolacji Studio i refaktoru repozytorium.
