# Session status (`session_status.py`)

Hub GicleeApp: [`README.md`](README.md)

Toolbar launchera: **Stan sesji** — tekstowy raport środowiska.

---

## Co sprawdza

| Obszar | Plik / źródło |
|--------|----------------|
| Sesja Shopify | `.shopify_session.json` — shop, scope, expiry |
| Konfig aplikacji | `shopify.app.toml` — mtime + opcjonalnie git last commit |
| Kursy NBP | `Komponenty/_shared/data/fx_cache.json` |
| Partners deploy | `Komponenty/_shared/data/partners_deploy_meta.json` (jeśli istnieje) |

---

## Odświeżenie sesji OAuth

Gdy raport pokazuje wygasły token:

```powershell
cd c:\Strona\pusty\cursor-api
npm run oauth
```

Szczegóły: [`../../docs/zaleznosci-wewnetrzne.md`](../../docs/zaleznosci-wewnetrzne.md)

---

## Kanoniczny shop

OAuth powinien zapisać `19v3bj-n0.myshopify.com` w polu `shop` — ten sam sklep co `gicleeart.eu`.

Alias CLI (`giclee-art-3.myshopify.com`) używany przy `theme push`, nie przy OAuth.
