"""Backfill redirectow /products/{stary-handle} po skryptach fix_*_titles.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import build_seo


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _old_pl_title(mod) -> str | None:
    if hasattr(mod, "OLD_PL_TITLE"):
        return str(getattr(mod, "OLD_PL_TITLE") or "").strip() or None
    olds = getattr(mod, "OLD_PL_TITLES", None)
    if olds:
        first = olds[0] if isinstance(olds, (list, tuple)) else olds
        return str(first or "").strip() or None
    return None


def main() -> int:
    shop, token = sc.load_session()
    scripts_dir = Path(__file__).resolve().parent
    seen_ids: set[int] = set()
    created = 0
    skipped = 0

    for script in sorted(scripts_dir.glob("fix_*_titles.py")):
        mod = _load_module(script)
        if not mod:
            continue
        product_id = int(getattr(mod, "PRODUCT_ID", 0) or 0)
        artist = str(getattr(mod, "ARTIST", "") or "").strip()
        old_title = _old_pl_title(mod)
        if not product_id or not artist or not old_title:
            print(f"POMIN: {script.name} — brak PRODUCT_ID/ARTIST/starego tytulu PL")
            skipped += 1
            continue
        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)

        _, _, old_handle = build_seo(tytul=old_title, artysta=artist, gatunek="", nurt="")
        prod = sc.get_product(shop, token, product_id)
        new_handle = (prod or {}).get("handle") or ""
        if not new_handle:
            print(f"POMIN: id={product_id} — brak produktu")
            skipped += 1
            continue
        if old_handle == new_handle:
            print(f"OK (bez zmiany): id={product_id} handle={new_handle}")
            continue

        sc.ensure_product_handle_redirect(shop, token, old_handle, new_handle)
        print(f"REDIRECT: /products/{old_handle} -> /products/{new_handle}")
        created += 1

    print(f"Gotowe: {created} redirectow, {skipped} pominieto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
