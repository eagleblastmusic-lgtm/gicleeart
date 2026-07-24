"""Przebudowa / utworzenie custom.story_pages: 1 akapit = 1 mini-strona.

- Produkty z metafieldem, które nie są już 1:1 → przebudowa; niepuste image
  ze starych stron przenoszone po kolei.
- Produkty bez metafielda → nowa konfiguracja 1:1 z pustymi image.
- details_image zachowywane bez zmian (gdy było).

Domyślnie dry-run. Zapis: --apply.

Przykład:
  python scripts/reflow_story_pages_one_per_paragraph.py
  python scripts/reflow_story_pages_one_per_paragraph.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.html_template import extract_paragraphs_from_body_html  # noqa: E402
from Komponenty.stronaproduktu.service import (  # noqa: E402
    load_catalog_with_story_status,
    normalize_story_config,
    save_story_config,
)


def _layout(pages: list[dict[str, Any]]) -> str:
    if not pages:
        return "(brak)"
    return "+".join(str(int(p.get("paragraphs") or 1)) for p in pages)


def _nonempty_images(pages: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for page in pages:
        image = str(page.get("image") or "").strip()
        if image:
            out.append(image)
    return out


def is_already_one_per_paragraph(pages: list[dict[str, Any]], paragraph_count: int) -> bool:
    if paragraph_count <= 0:
        return False
    if len(pages) != paragraph_count:
        return False
    return all(int(p.get("paragraphs") or 0) == 1 for p in pages)


def build_one_per_paragraph_config(
    old_config: dict[str, Any] | None,
    paragraph_count: int,
) -> dict[str, Any]:
    """N stron po 1 akapicie; niepuste image ze starych stron po kolei."""
    n = max(1, int(paragraph_count))
    old_pages = list((old_config or {}).get("pages") or [])
    images = _nonempty_images(old_pages)
    pages: list[dict[str, Any]] = []
    for i in range(n):
        pages.append({"paragraphs": 1, "image": images[i] if i < len(images) else ""})
    out: dict[str, Any] = {"pages": pages}
    details = str((old_config or {}).get("details_image") or "").strip()
    if details:
        out["details_image"] = details
    return normalize_story_config(out)


def _fetch_body_html(shop: str, token: str, product_id: int) -> str:
    prod = sc.get_product(shop, token, int(product_id))
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu {product_id}.")
    return str(prod.get("body_html") or "")


def run(*, apply: bool) -> int:
    shop, token = sc.load_session()
    print("Pobieram katalog + custom.story_pages...")
    rows = load_catalog_with_story_status(logger=print)
    print(f"Produktów w katalogu: {len(rows)}")

    skipped_ok = 0
    skipped_no_paragraphs = 0
    to_update: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, row in enumerate(rows, start=1):
        pid = int(row.get("product_id") or 0)
        handle = str(row.get("handle") or pid).strip()
        if not pid:
            continue
        try:
            body = _fetch_body_html(shop, token, pid)
            paragraphs = extract_paragraphs_from_body_html(body)
            n = len(paragraphs)
            if n <= 0:
                skipped_no_paragraphs += 1
                continue

            old_cfg = row.get("story_config") if row.get("has_story") else None
            if isinstance(old_cfg, dict):
                old_pages = list(old_cfg.get("pages") or [])
            else:
                old_pages = []
                old_cfg = None

            if old_cfg is not None and is_already_one_per_paragraph(old_pages, n):
                skipped_ok += 1
                if idx % 50 == 0:
                    print(f"  … przejrzano {idx}/{len(rows)}")
                continue

            new_cfg = build_one_per_paragraph_config(old_cfg, n)
            images_moved = min(len(_nonempty_images(old_pages)), len(new_cfg["pages"]))
            action = "reflow" if old_cfg is not None else "create"
            to_update.append(
                {
                    "product_id": pid,
                    "handle": handle,
                    "action": action,
                    "old_layout": _layout(old_pages),
                    "new_layout": _layout(new_cfg["pages"]),
                    "paragraph_count": n,
                    "images_moved": images_moved,
                    "config": new_cfg,
                }
            )
            print(
                f"{action.upper()} {handle}: {_layout(old_pages)} -> {_layout(new_cfg['pages'])} "
                f"(akapity={n}, grafiki={images_moved})"
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"{handle} (pid={pid}): {exc}"
            errors.append(msg)
            print(f"ERROR {msg}")

    create_n = sum(1 for i in to_update if i["action"] == "create")
    reflow_n = sum(1 for i in to_update if i["action"] == "reflow")
    print()
    print(f"skipped_ok={skipped_ok}")
    print(f"skipped_no_paragraphs={skipped_no_paragraphs}")
    print(f"to_update={len(to_update)} (create={create_n}, reflow={reflow_n})")
    print(f"errors={len(errors)}")

    if not apply:
        print("Dry-run — bez zapisu. Uruchom z --apply, aby zapisać.")
        return 1 if errors and not to_update else 0

    updated = 0
    for item in to_update:
        pid = int(item["product_id"])
        handle = item["handle"]
        try:
            result = save_story_config(pid, item["config"], logger=None)
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "save_story_config failed")
            updated += 1
            if updated % 25 == 0 or updated == len(to_update):
                print(f"SAVED {updated}/{len(to_update)} … ostatni: {handle}")
        except Exception as exc:  # noqa: BLE001
            msg = f"save {handle} (pid={pid}): {exc}"
            errors.append(msg)
            print(f"ERROR {msg}")

    print()
    print(f"skipped_ok={skipped_ok}")
    print(f"updated={updated}")
    print(f"errors={len(errors)}")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Zapisz metafieldy do Shopify (bez tej flagi tylko dry-run).",
    )
    args = parser.parse_args()
    return run(apply=bool(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
