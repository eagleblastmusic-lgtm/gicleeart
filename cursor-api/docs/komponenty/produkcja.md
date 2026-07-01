# Komponent: produkcja

Hub: [`README.md`](README.md)

**Cel:** Śledzenie statusu zamówień Shopify — wydruk, ramka (utwardzanie 3 dni), składanie, pakowanie, wysyłka. Etykiety, statystyki, sync z Admin.

---

## Wejście / wyjście

| Wejście | Wyjście |
|---------|---------|
| Zamówienia Shopify (`read_orders`) | Lokalna baza `dane/zamowienia.json` |
| Warianty (rozmiar, rama) | Etykiety HTML, statusy produkcji |

---

## Kluczowe pliki

| Plik | Rola |
|------|------|
| `view.py` | GUI inline w GicleeApp |
| `orders_sync.py` | Polling Shopify → `zamowienia.json` |
| `frame_variant.py` | Parsowanie tytułu wariantu (rama, rozmiar) |
| `passepartout.py` | Kolor passepartout z `line.properties[Passepartout]` |
| `label_html.py` | Generowanie etykiet |
| `shipping.py` | Integracja wysyłki |
| `web_server.py` | Opcjonalny podgląd www |
| `dane/zamowienia.json` | Baza lokalna |

---

## Zależności

| Moduł | Od czego |
|-------|----------|
| `dodajobraz/shopify_client.py` | REST orders API |
| `_shared/tree_sort.py` | Sortowanie list |

**Warstwa pusty:** zamówienia „Własna fotografia” widoczne w sync, ale pliki klienta **nie** są pobierane z R2 (luka — patrz niżej).

---

## Luka integracji: własna fotografia

Komponent widzi pozycje produktu „Własna fotografia” w zamówieniach, ale **nie czyta** `_Upload ID` ani plików z R2.  
Pliki klienta trafiają mailem z Workera ([`../worker/mockup-order-worker.md`](../worker/mockup-order-worker.md)).

Mapa: [`../../../docs/zaleznosci.md`](../../../docs/zaleznosci.md) → *Produkcja bez pliku klienta*

---

## SHOP_KNOWLEDGE

§9d — komponent produkcja

---

## Typowe błędy

| Objaw | Sprawdź |
|-------|---------|
| Brak nowych zamówień | `sync_state.json`, scope `read_orders` |
| Zły wariant ramy | `frame_variant.py`, tytuł wariantu Shopify |
| Brak koloru passepartout | Property `Passepartout` na pozycji koszyka (motyw) |

→ [`../troubleshooting.md`](../troubleshooting.md)
