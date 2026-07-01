"""Dodaje artyste do menu nawigacji (pozycja COLLECTION pod 'Katalog'), na wzor pozostalych.

Uzycie:
    python add_artist_to_menu.py "Butti, Lorenzo"
    python add_artist_to_menu.py "Butti, Lorenzo" --create-collection
    python add_artist_to_menu.py "Butti, Lorenzo" --parent Katalog --menu main-menu

Wymaga aktywnej sesji (.shopify_session.json) ze scope:
    read_online_store_navigation, write_online_store_navigation
(po dodaniu scope: `npm run deploy` + `npm run oauth`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "Komponenty" / "dodajobraz"))

import shopify_client as sc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("title", help="Tytul artysty w formacie 'Nazwisko, Imie'")
    ap.add_argument("--parent", default="ARTYŚCI", help="Pozycja nadrzedna menu (domyslnie 'ARTYŚCI')")
    ap.add_argument("--menu", default=None, help="Handle menu (np. 'main-menu'); domyslnie auto-wykrycie po parencie")
    ap.add_argument(
        "--create-collection",
        action="store_true",
        help="Utworz custom-collection o tym tytule, jesli nie istnieje",
    )
    args = ap.parse_args()

    title = args.title.strip()
    shop, token = sc.load_session()
    print(f"Sklep: {shop}")

    coll = sc.find_artist_collection(shop, token, title)
    if coll:
        cid = int(coll["id"])
        print(f"Kolekcja istnieje: '{coll['title']}' (id={cid}, {coll['kind']})")
    elif args.create_collection:
        created = sc.create_custom_collection(shop, token, title=title)
        cid = int(created["id"])
        print(f"Utworzono custom-collection: '{title}' (id={cid})")
    else:
        print(
            f"BLAD: brak kolekcji '{title}'. Uzyj --create-collection albo utworz ja recznie."
        )
        return 2

    gid = sc.collection_gid(cid)
    res = sc.add_menu_child_collection(
        shop,
        token,
        parent_title=args.parent,
        child_title=title,
        collection_gid=gid,
        menu_handle=args.menu,
    )
    if res["created"]:
        print(f"OK: dodano '{title}' pod '{args.parent}' w menu '{res['menu_handle']}'.")
    else:
        print(f"Pominieto: '{title}' juz istnieje pod '{args.parent}' (menu '{res['menu_handle']}').")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
