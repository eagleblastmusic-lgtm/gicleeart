# Worker — indeks (Cloudflare)

Hub warstwy API: [`../README.md`](../README.md)

Programy w chmurze — działają bez włączonego PC.

| Worker | Folder kodu | Dokument |
|--------|-------------|----------|
| Upload zdjęć klienta + mail po zamówieniu | `mockup-order-worker/` | [`mockup-order-worker.md`](mockup-order-worker.md) |

Inne integracje chmurowe (zoom R2 itd.): [`../komponenty/dodajobraz.md`](../komponenty/dodajobraz.md) · [`../../SHOP_KNOWLEDGE.md`](../../SHOP_KNOWLEDGE.md)

Powiązany front (motyw): [`../../../docs/motyw/mockup-wlasna-fotografia.md`](../../../docs/motyw/mockup-wlasna-fotografia.md)

---

## Szybki deploy mockup-order-worker

```powershell
cd c:\Strona\pusty\cursor-api\mockup-order-worker
npx wrangler deploy
```

Sekrety: `RESEND_API_KEY`, `SHOPIFY_WEBHOOK_SECRET` (`wrangler secret put …`).

Szczegóły: [`mockup-order-worker.md`](mockup-order-worker.md) · [`../../mockup-order-worker/WDROZENIE.md`](../../mockup-order-worker/WDROZENIE.md)
