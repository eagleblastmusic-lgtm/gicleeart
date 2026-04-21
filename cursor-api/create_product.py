"""
Tworzy nowy produkt w sklepie (REST Admin API). Wymaga .shopify_session.json (npm run oauth).

Przykład:
  python create_product.py --title "Test z Cursora" --price 49.99
  python create_product.py --title "Test z Cursora" --price 1 --image "H:\\sciezka\\zdjecie.png"
  python create_product.py --title "Obraz" --price 120 --body-html "<p>Opis HTML</p>" --vendor "Giclee Art"

Zdjęcie: lokalny plik (PNG/JPG) — wgrywane jako pierwszy obraz produktu (base64 przez REST).
"""
from __future__ import annotations

import argparse
import base64
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = ROOT / ".shopify_session.json"
API_VERSION = "2026-04"


def load_session() -> tuple[str, str]:
    if not SESSION.is_file():
        raise SystemExit(f"Brak {SESSION}. Uruchom: npm run oauth")
    data = json.loads(SESSION.read_text(encoding="utf-8"))
    shop = (data.get("shop") or "").strip()
    token = (data.get("accessToken") or "").strip()
    if not shop or not token:
        raise SystemExit("Niepełna sesja w .shopify_session.json")
    return shop, token


def create_product(
    shop: str,
    token: str,
    *,
    title: str,
    price: str,
    body_html: str | None,
    vendor: str | None,
    product_type: str | None,
    status: str,
) -> dict:
    url = f"https://{shop}/admin/api/{API_VERSION}/products.json"
    product: dict = {
        "title": title,
        "status": status,
        "variants": [{"price": price}],
    }
    if body_html is not None:
        product["body_html"] = body_html
    if vendor:
        product["vendor"] = vendor
    if product_type:
        product["product_type"] = product_type

    payload = json.dumps({"product": product}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def add_product_image(
    shop: str,
    token: str,
    product_id: int,
    image_path: Path,
    *,
    alt: str | None,
) -> dict:
    """Dodaje obraz do produktu (POST .../products/{id}/images.json)."""
    raw = image_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    url = f"https://{shop}/admin/api/{API_VERSION}/products/{product_id}/images.json"
    image_obj: dict = {
        "attachment": b64,
        "filename": image_path.name,
    }
    if alt:
        image_obj["alt"] = alt
    payload = json.dumps({"image": image_obj}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Utwórz produkt w Shopify")
    p.add_argument("--title", required=True, help="Tytuł produktu")
    p.add_argument(
        "--price",
        default="0.00",
        help='Cena pierwszego wariantu (np. "29.99"), waluta ze sklepu',
    )
    p.add_argument("--body-html", default=None, help="Opis HTML (opcjonalnie)")
    p.add_argument("--vendor", default=None)
    p.add_argument("--product-type", default=None, dest="product_type")
    p.add_argument(
        "--status",
        default="draft",
        choices=("draft", "active", "archived"),
        help="draft = szkic, active = opublikowany",
    )
    p.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Ścieżka do pliku graficznego (PNG/JPG) — pierwsze zdjęcie produktu",
    )
    p.add_argument(
        "--image-alt",
        default=None,
        dest="image_alt",
        help="Tekst alternatywny (alt) dla zdjęcia",
    )
    args = p.parse_args()

    shop, token = load_session()
    try:
        out = create_product(
            shop,
            token,
            title=args.title,
            price=str(args.price),
            body_html=args.body_html,
            vendor=args.vendor,
            product_type=args.product_type,
            status=args.status,
        )
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode("utf-8", errors="replace"))
        raise SystemExit(1) from e

    prod = out.get("product", {})
    pid = prod.get("id")
    print("Utworzono produkt:")
    print(f"  ID:   {pid}")
    print(f"  Tytuł: {prod.get('title')}")
    print(f"  Handle: {prod.get('handle')}")
    print("  W panelu: Produkty — znajdziesz po tytule lub szukaj po ID.")
    v0 = (prod.get("variants") or [{}])[0]
    print(f"  Cena (pierwszy wariant): {v0.get('price')}")

    if args.image:
        pth = args.image.expanduser().resolve()
        if not pth.is_file():
            raise SystemExit(f"Brak pliku obrazu: {pth}")
        try:
            img_out = add_product_image(
                shop,
                token,
                int(pid),
                pth,
                alt=args.image_alt or args.title,
            )
        except urllib.error.HTTPError as e:
            print(f"Błąd wgrywania zdjęcia HTTP {e.code}")
            print(e.read().decode("utf-8", errors="replace"))
            raise SystemExit(1) from e
        img = img_out.get("image", {})
        src = str(img.get("src") or "")
        print("  Zdjęcie dodane:")
        print(f"    src: {src[:80]}…" if len(src) > 80 else f"    src: {src}")
        print(f"    id obrazu: {img.get('id')}")


if __name__ == "__main__":
    main()
