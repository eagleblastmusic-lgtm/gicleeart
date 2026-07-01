"""Korekta: usuniecie alternatyw bedacych tylko tytulem bez artykulu (Bruegel)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.fix_bruegel_batch6_titles import PRODUCTS, _apply_product
from Komponenty.dodajobraz import shopify_client as sc

PATCH_IDS = {15610433995100, 15610441302364}


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        if cfg["product_id"] not in PATCH_IDS:
            continue
        _apply_product(shop, token, cfg)
    print("\nGotowe — 2 produkty Bruegel (article-only alts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
