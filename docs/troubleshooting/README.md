# Troubleshooting — indeks

Hub integracyjny: [`../README.md`](../README.md)  
**Macierz symptom → warstwa → plik:** [`../zaleznosci.md`](../zaleznosci.md)

---

## Według warstwy

| Warstwa | Dokument |
|---------|----------|
| **Motyw (pusty)** | [`../motyw/troubleshooting.md`](../motyw/troubleshooting.md) — layout, deploy, mockup UI |
| **API (cursor-api)** | [`../../cursor-api/docs/troubleshooting.md`](../../cursor-api/docs/troubleshooting.md) — Worker, OAuth, R2, Python |
| **GicleeApp** | [`../../cursor-api/giclee_app/docs/troubleshooting.md`](../../cursor-api/giclee_app/docs/troubleshooting.md) — launcher, kafelki, exe |

---

## Scenariusze cross-warstwowe (najczęstsze)

### Brak maila po opłaconym zamówieniu

1. [`../zaleznosci.md`](../zaleznosci.md) → macierz diagnozy
2. [`../../cursor-api/docs/worker/mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md)
3. Shopify Admin → `_Upload ID` w properties linii

### Upload nie działa / błąd w koszyku

→ [`../motyw/mockup-wlasna-fotografia.md`](../motyw/mockup-wlasna-fotografia.md) + [`../../cursor-api/docs/troubleshooting.md`](../../cursor-api/docs/troubleshooting.md) (CORS)

### Po „Dodaj do koszyka” brak scrollu lub koszyk za wcześnie

→ [`../motyw/mockup-wlasna-fotografia.md`](../motyw/mockup-wlasna-fotografia.md) — sekcja „Przepływ Dodaj do koszyka (UI)” · [`../motyw/troubleshooting.md`](../motyw/troubleshooting.md)

### Niska jakość pliku w mailu

→ [`../../cursor-api/docs/worker/mockup-order-worker.md`](../../cursor-api/docs/worker/mockup-order-worker.md) — `original-full.jpg` vs `original.*`

### Python / reprodukcje / OAuth

→ [`../../cursor-api/docs/troubleshooting.md`](../../cursor-api/docs/troubleshooting.md) · [`../../cursor-api/SHOP_KNOWLEDGE.md`](../../cursor-api/SHOP_KNOWLEDGE.md)

Notatki FAQ: `cursor-api/Komponenty/notatnik/notatki/05-faq-i-trobleshoot.md`
