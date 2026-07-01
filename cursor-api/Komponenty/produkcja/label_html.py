"""Eksport prostych etykiet warsztatowych do HTML (druk / PDF z przegladarki)."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def write_workshop_labels_html(path: Path, orders: list[dict[str, Any]], *, title: str = "Etykiety") -> None:
    """Zapisuje HTML z kartami etykiet (ok. 85mm wysokosci) do druku."""
    cards: list[str] = []
    for o in orders:
        oid = html.escape(str(o.get("id") or ""))
        client = html.escape(str(o.get("client") or ""))
        tit = html.escape(str(o.get("tytul_obrazu") or ""))
        d = html.escape(str(o.get("ramka_drewno") or ""))
        r = html.escape(str(o.get("ramka_rozmiar") or ""))
        k = html.escape(str(o.get("ramka_kolor") or ""))
        pp = html.escape(str(o.get("passepartout_kolor") or ""))
        qty = html.escape(str(o.get("ilosc") or 1))
        shop_no = html.escape(str(o.get("shopify_order_no") or ""))
        cards.append(
            f"""
<div class="card">
  <div class="id">{oid}</div>
  <div class="row"><strong>Klient:</strong> {client}</div>
  <div class="row"><strong>Tytul:</strong> {tit}</div>
  <div class="row"><strong>Drewno:</strong> {d} &nbsp;|&nbsp; <strong>Rozm.:</strong> {r}</div>
  <div class="row"><strong>Kolor:</strong> {k} &nbsp;|&nbsp; <strong>Passepartout:</strong> {pp or "—"}</div>
  <div class="row"><strong>Ilosc:</strong> {qty}</div>
  <div class="shopify">{shop_no}</div>
</div>"""
        )

    body = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 12px; color: #111; }}
  .card {{
    border: 2px solid #333; border-radius: 6px; padding: 10px 12px; margin-bottom: 14px;
    page-break-inside: avoid; max-width: 100mm;
  }}
  .id {{ font-size: 18px; font-weight: bold; margin-bottom: 6px; color: #0d47a1; }}
  .row {{ font-size: 13px; margin: 3px 0; line-height: 1.35; }}
  .shopify {{ font-size: 11px; color: #666; margin-top: 6px; }}
  @media print {{
    body {{ margin: 0; }}
    .card {{ border-color: #000; }}
  }}
</style>
</head>
<body>
<h1 style="font-size:16px;margin:0 0 10px 0;">{html.escape(title)}</h1>
{"".join(cards)}
</body>
</html>"""
    path.write_text(body, encoding="utf-8")
