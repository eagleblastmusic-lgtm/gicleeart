"""Ponownie sortuje liste artystow w menu (pozycja ARTYŚCI) po nazwisku z czastkami (van, ter, …).

Uzycie:
    python scripts/resort_artists_menu.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402


def main() -> int:
    shop, token = sc.load_session()
    res = sc.resort_artist_menu_children(shop, token)
    print(
        f"OK: posortowano {res.get('count', 0)} pozycji pod ARTYŚCI "
        f"(menu '{res.get('menu_handle')}')."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
