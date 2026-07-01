# Koszyk — prośba o fakturę

**Hover w ciemnym drawerze:** `scheme-1` ma `primary_hover` = czarny; globalne `summary:hover` i `p>a:hover` w `base.css` przez to gasiły białe napisy (nagłówki sekcji, tytuły produktów). Nadpisanie w `assets/custom.css` (ładuje się na każdej stronie). Przycisk **Zrealizuj zakup** w drawerze: czarne tło, biały tekst, złoty obrys (`#c6a96b`); hover — jaśniejszy obrys i delikatna poświata. Tytuł produktu po najechaniu tylko lekko przygasza (bez podkreślenia).

Sekcja w podsumowaniu koszyka (strona koszyka + drawer), włączana ustawieniem motywu **Prośba o fakturę w koszyku** (`show_cart_invoice_request`).

## Pliki

| Plik | Rola |
|------|------|
| `snippets/cart-invoice-request.liquid` | UI: checkbox, osoba prywatna / firma, pola firmy |
| `assets/cart-invoice-request.js` | Zapis `cart.attributes` przez `/cart/update.js` |
| `snippets/cart-summary.liquid` | Render sekcji |
| `locales/*.json` | Tłumaczenia PL, EN, DE, FR, ES, IT, NL (+ fallback EN) |

## Atrybuty zamówienia

Po checkout trafiają do `note_attributes`:

| Klucz | Wartość |
|-------|---------|
| `_Invoice requested` | `yes` lub puste |
| `_Invoice type` | `private` / `company` |
| `_Company name` | nazwa firmy |
| `_Tax ID` | NIP (PL) lub VAT / Tax ID (rynek zagraniczny) |

Etykieta pola podatkowego zależy od `localization.country.iso_code` (PL → NIP, DE → USt-IdNr., FR → n° TVA, …).

## GicleeApp

`Komponenty/dokumentysprzedazy/order_attributes.py` — odczyt z zamówienia; kolumna **Faktura?** w liście zamówień; szkic faktury wstawia dane firmy.

→ [`dokumentysprzedazy.md`](../../cursor-api/docs/komponenty/dokumentysprzedazy.md)
