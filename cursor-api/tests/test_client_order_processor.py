"""Testy parsera zamówień własna fotografia (bez IMAP)."""

from __future__ import annotations

from Komponenty.poczta.client_order_processor import (
    _apply_index_suffix,
    _build_download_plan,
    _folder_name_for_order,
    is_custom_photo_order_subject,
    parse_order_email,
)

SAMPLE_HTML = """
<h2>Własna fotografia — nowe zamówienie</h2>
<p><strong>Numer zamówienia:</strong> #1001</p>
<p>ID Shopify: 5678901234</p>
<p><strong>Klient:</strong> Jan Kowalski<br><strong>E-mail:</strong> jan@example.com</p>
<hr>
<h3>Własna fotografia</h3>
<p><strong>Ilość:</strong> 1</p>
<h4>RAMKA</h4>
<p>Rozmiar: A4 · Kolor: czarny</p>
<h4>PLIKI</h4>
<p>Upload ID: 11111111-2222-4333-8444-555555555555</p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid1/original-full.jpg">📷 Oryginał zdjęcia klienta (max. jakość)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid1/preview.jpg">🖼 Podgląd mockupu (kadrowanie)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid1/crop.json">📐 Dane kadrowania (JSON)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid1/meta.json">meta.json</a></p>
"""

SAMPLE_HTML_MULTI = """
<h2>Własna fotografia — nowe zamówienie</h2>
<p><strong>Numer zamówienia:</strong> #1007</p>
<p><strong>Klient:</strong> Dada Dada<br><strong>E-mail:</strong> adagiotomaso@gmail.com</p>
<hr>
<h3>Własna fotografia</h3>
<p><strong>Ilość:</strong> 1</p>
<h4>RAMKA</h4>
<p>Rozmiar: XL · Drewno: Dąb</p>
<h4>PLIKI</h4>
<p>Upload ID: 0340416c-71ba-47eb-b85a-368038ef626f</p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-a/original-full.jpg">📷 Oryginał zdjęcia klienta (max. jakość)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-a/preview.jpg">🖼 Podgląd mockupu (kadrowanie)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-a/crop.json">📐 Dane kadrowania (JSON)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-a/meta.json">meta.json</a></p>
<hr>
<h3>Własna fotografia</h3>
<p><strong>Ilość:</strong> 1</p>
<h4>RAMKA</h4>
<p>Rozmiar: M · Drewno: Dąb</p>
<h4>PLIKI</h4>
<p>Upload ID: fc854c38-ef19-42c3-8e10-90113e745668</p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-b/original-full.jpg">📷 Oryginał zdjęcia klienta (max. jakość)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-b/preview.jpg">🖼 Podgląd mockupu (kadrowanie)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-b/crop.json">📐 Dane kadrowania (JSON)</a></p>
<p><a href="https://pub.example.r2.dev/customer-uploads/uuid-b/meta.json">meta.json</a></p>
"""


def test_subject_match() -> None:
    assert is_custom_photo_order_subject("Giclée — zamówienie #1001 — własna fotografia")
    assert is_custom_photo_order_subject("WŁASNA FOTOGRAFIA test")
    assert not is_custom_photo_order_subject("Newsletter")


def test_parse_order_email() -> None:
    order = parse_order_email(SAMPLE_HTML, "Giclée — zamówienie #1001 — własna fotografia")
    assert order is not None
    assert order.order_number == "#1001"
    assert order.customer_name == "Jan Kowalski"
    assert order.customer_email == "jan@example.com"
    assert len(order.items) == 1
    item = order.items[0]
    assert item.upload_id == "11111111-2222-4333-8444-555555555555"
    assert "original-full.jpg" in item.original_url
    assert "preview.jpg" in item.preview_url
    assert item.crop_url.endswith("crop.json")
    assert item.meta_url.endswith("meta.json")


def test_parse_order_email_multi_item() -> None:
    order = parse_order_email(SAMPLE_HTML_MULTI, "Giclée — zamówienie #1007 — własna fotografia")
    assert order is not None
    assert len(order.items) == 2
    assert order.items[0].index == 1
    assert order.items[1].index == 2
    assert order.items[0].upload_id == "0340416c-71ba-47eb-b85a-368038ef626f"
    assert order.items[1].upload_id == "fc854c38-ef19-42c3-8e10-90113e745668"
    assert "uuid-a" in order.items[0].original_url
    assert "uuid-b" in order.items[1].original_url
    assert order.items[0].frame_lines
    assert "XL" in order.items[0].frame_lines[0]
    assert "M" in order.items[1].frame_lines[0]


def test_apply_index_suffix() -> None:
    assert _apply_index_suffix("Oryginał zdjęcia klienta.jpg", 1, 1) == "Oryginał zdjęcia klienta.jpg"
    assert _apply_index_suffix("Oryginał zdjęcia klienta.jpg", 1, 2) == "Oryginał zdjęcia klienta_1.jpg"
    assert _apply_index_suffix("meta.json", 2, 2) == "meta_2.json"


def test_build_download_plan_multi() -> None:
    order = parse_order_email(SAMPLE_HTML_MULTI, "Giclée — zamówienie #1007 — własna fotografia")
    assert order is not None
    plan = _build_download_plan(order)
    names = [fname for _url, fname, _label in plan]
    assert "Oryginał zdjęcia klienta_1.jpg" in names
    assert "Oryginał zdjęcia klienta_2.jpg" in names
    assert "meta_1.json" in names
    assert "meta_2.json" in names
    assert len(plan) == 8


def test_folder_name_windows_safe() -> None:
    name = _folder_name_for_order("#1001")
    assert ":" not in name
    assert "#1001" in name
