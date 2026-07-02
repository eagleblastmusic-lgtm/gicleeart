# MATKA — skrót startowy (agent czyta automatycznie)

> Agent wczytuje ten plik na starcie rozmowy (reguła `.cursor/rules/dokumentacja.mdc`). Wklejka opcjonalna — tylko jedna linia z modułem, np. „Warstwa: motyw, moduł: karuzela showcase”.  
> **Szczegóły, scenariusze, ID:** [`docs/README.md`](docs/README.md) · **diagnoza:** [`docs/zaleznosci.md`](docs/zaleznosci.md) · **konta:** [`USLUGI.md`](USLUGI.md)

---

## Gdzie jest kod / docs

| Warstwa | Kod | Hub docs |
|---------|-----|----------|
| Motyw Shopify | korzeń `pusty/` | [`docs/motyw/README.md`](docs/motyw/README.md) |
| API, Worker, komponenty | `cursor-api/` | [`cursor-api/docs/README.md`](cursor-api/docs/README.md) |
| GicleeApp (launcher) | `cursor-api/giclee_app/` | [`cursor-api/giclee_app/docs/README.md`](cursor-api/giclee_app/docs/README.md) |

Archiwum (czytaj sekcje, **nie pisz**): [`THEME_KNOWLEDGE.md`](THEME_KNOWLEDGE.md) · [`cursor-api/SHOP_KNOWLEDGE.md`](cursor-api/SHOP_KNOWLEDGE.md)

---

## Główne ścieżki (→ plik modułowy)

1. **Własna fotografia** — motyw + Worker → [`docs/motyw/mockup-wlasna-fotografia.md`](docs/motyw/mockup-wlasna-fotografia.md)
2. **Reprodukcja klasyka** — `dodajobraz` → [`cursor-api/docs/komponenty/dodajobraz.md`](cursor-api/docs/komponenty/dodajobraz.md)
3. **Mockup katalogowy CZB** — `Komponenty/mockup/` (**≠** mockup klienta) → [`cursor-api/docs/komponenty/mockup-katalogowy.md`](cursor-api/docs/komponenty/mockup-katalogowy.md)
4. **Produkcja** — [`cursor-api/docs/komponenty/produkcja.md`](cursor-api/docs/komponenty/produkcja.md)
5. **Księgowość / finanse** — hub `finanse` → [`cursor-api/docs/komponenty/finanse.md`](cursor-api/docs/komponenty/finanse.md)
6. **Limity / poczta / Meta** — [`cursor-api/docs/komponenty/limity.md`](cursor-api/docs/komponenty/limity.md) · [`poczta.md`](cursor-api/docs/komponenty/poczta.md)

Problem → plik: tabela w [`docs/README.md`](docs/README.md#problem--gdzie).

---

## Deploy (skrót)

```powershell
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live --only "ścieżka"
cd cursor-api\mockup-order-worker && npx wrangler deploy
cd cursor-api && pythonw -m giclee_app
```

---

## Zasady dla AI

1. **Prawda** = pliki w `docs/…` i `cursor-api/docs/…` — tam zapisuj zmiany.
2. Jedna warstwa naraz; mockup klienta ≠ `Komponenty/mockup/`.
3. Nie czytaj całego SHOP/THEME — jeden plik modułowy + ewentualna sekcja archiwum.

---

## Aktualizacja dokumentacji (obowiązkowo)

Po ważnej zmianie — w tej samej sesji, bez pytania (chyba że user: „bez docs”).

**Ważne:** przepływ, ID, endpoint, komponent, zależność warstw, diagnoza, deploy.

| Gdzie | Co |
|-------|-----|
| `cursor-api/docs/komponenty/<moduł>.md` lub `docs/motyw/…` | **Główny opis zmiany** |
| `docs/zaleznosci.md` | cross-warstwowe |
| `cursor-api/giclee_app/docs/` | launcher, kafelki |
| `MATKA.md` | tylko skrót: nowa trasa, ID, link do pliku modułowego |
| `USLUGI.md` | konta, plany, limity zewnętrzne |
| `docs/README.md` | nowy scenariusz / wpis „problem → gdzie” |

**Nie aktualizuj** `SHOP_KNOWLEDGE.md` / `THEME_KNOWLEDGE.md` (archiwum). Krótko: co, dlaczego, jak zweryfikować. Bez sekretów.
