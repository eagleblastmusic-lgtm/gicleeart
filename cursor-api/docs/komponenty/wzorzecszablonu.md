# Komponent: wzorzecszablonu

**Cel:** Masowe i pojedyncze przypisanie **wzorca szablonu motywu** (`template_suffix`) produktom typu Obraz — odpowiednik pola «Wzorzec szablonu» w Shopify Admin.

**Nie mylić z:** [`wyborszablonu.md`](wyborszablonu.md) (szablony **wariantów** cen/opcji w `variant_templates.json`).

---

## Pliki

| Plik | Rola |
|------|------|
| `Komponenty/wzorzecszablonu/gui.py` | Lista produktów, filtr, combobox wzorców, zastosowanie hurtowe |
| `Komponenty/wzorzecszablonu/service.py` | Shopify REST (`template_suffix`), skan `templates/product*.json` |
| `Komponenty/wzorzecszablonu/component.json` | Metadane kafelka launchera |

Tryb: `subprocess`. Sekcja launchera: **Administracja strony** (kafelek «Wzorzec szablonu»).

---

## Źródło listy wzorców

1. Pliki `templates/product.json` i `templates/product.<suffix>.json` w **repo motywu** (katalog nad `cursor-api/`).
2. Sufiksy już ustawione na produktach w sklepie (union — np. stary wzorzec przed usunięciem pliku).

API motywu (`read_themes`) nie jest wymagane — token aplikacji go nie ma; po dodaniu nowego pliku szablonu w motywie wystarczy **Odśwież listę** w komponencie.

Mapowanie: `templates/product.json` → «Domyślny produkt»; `templates/product.szablon-produktu-v3.json` → `szablon-produktu-v3`.

Szablony PDP w motywie: [`../../../docs/motyw/szablony-i-strony.md`](../../../docs/motyw/szablony-i-strony.md).

---

## Użycie (GicleeApp)

1. Kafelek **Wzorzec szablonu**.
2. Lista produktów Obraz z kolumną bieżącego wzorca.
3. Zaznacz jeden lub wiele wierszy (Ctrl / Shift).
4. Wybierz wzorzec z listy → **Zastosuj do zaznaczonych**.
5. **👁** — otwiera produkt w Shopify Admin (podgląd jak w panelu sklepu).

Filtr tekstowy + filtr po wzorcu u góry tabeli.

---

## Shopify

- Pole REST: `product.template_suffix` (pusty = domyślny `product.json`).
- Zapis: `PUT /admin/api/.../products/{id}.json` przez `shopify_client.update_product`.

Powiązane komponenty motywu PDP: [`przedpo.md`](przedpo.md) (v2), [`stronaproduktu.md`](stronaproduktu.md) (v3).
