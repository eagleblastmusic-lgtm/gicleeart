"""Jednorazowo: «Gogh, Vincent van» → «Van Gogh, Vincent» (kolekcja + menu Katalog)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.shopify_client import ShopifyError  # noqa: E402

OLD_TITLE = "Gogh, Vincent van"
NEW_TITLE = "Van Gogh, Vincent"
CATALOG_PARENT = "ARTYŚCI"
MENU_HANDLE = "main-menu"


def _rename_in_menu_items(items: list[dict], old: str, new: str) -> bool:
    changed = False
    old_key = old.strip().casefold()
    for it in items or []:
        if (it.get("title") or "").strip().casefold() == old_key:
            it["title"] = new
            changed = True
        if it.get("items") and _rename_in_menu_items(it["items"], old, new):
            changed = True
    return changed


def _sort_menu_children(items: list[dict]) -> None:
    from Komponenty.dodajobraz.parser import catalog_artist_sort_key

    for it in items or []:
        children = it.get("items") or []
        if children:
            children.sort(key=lambda ch: catalog_artist_sort_key(ch.get("title") or ""))
            it["items"] = children
            _sort_menu_children(children)


def rename_collection_title(shop: str, token: str, coll: dict, new_title: str) -> dict:
    coll_id = int(coll["id"])
    kind = coll.get("kind") or "custom"
    key = "custom_collection" if kind == "custom" else "smart_collection"
    path = f"{kind}_collections/{coll_id}.json"
    payload = {key: {"id": coll_id, "title": new_title}}
    out = sc.rest_put(shop, token, path, payload)
    return (out or {}).get(key) or {}


def rename_menu_entry(shop: str, token: str) -> dict:
    menu = sc.find_menu(shop, token, handle=MENU_HANDLE)
    if menu is None:
        menu = sc.find_menu(shop, token, contains_item_title=OLD_TITLE)
    if not menu:
        raise ShopifyError("Nie znaleziono menu z pozycja Van Gogha.")

    items = [sc._item_to_input(it) for it in (menu.get("items") or [])]
    if not _rename_in_menu_items(items, OLD_TITLE, NEW_TITLE):
        alt_old = "Van Gogh, Vincent"
        if not _rename_in_menu_items(items, alt_old, NEW_TITLE):
            raise ShopifyError(f"W menu brak pozycji «{OLD_TITLE}».")

    parent = sc._find_input_by_title(items, CATALOG_PARENT)
    if parent and parent.get("items"):
        from Komponenty.dodajobraz.parser import catalog_artist_sort_key, format_catalog_artist_title

        for ch in parent["items"]:
            raw = (ch.get("title") or "").strip()
            if raw:
                ch["title"] = format_catalog_artist_title(raw)
        parent["items"].sort(key=lambda ch: catalog_artist_sort_key(ch.get("title") or ""))

    mutation = (
        "mutation MenuUpdate($id: ID!, $title: String!, $handle: String!, "
        "$items: [MenuItemUpdateInput!]!) { "
        "menuUpdate(id: $id, title: $title, handle: $handle, items: $items) { "
        "menu { id handle title } userErrors { field message } } }"
    )
    res = sc.graphql(
        shop,
        token,
        mutation,
        {
            "id": menu["id"],
            "title": menu["title"],
            "handle": menu["handle"],
            "items": items,
        },
    )
    payload = res.get("menuUpdate") or {}
    errs = payload.get("userErrors") or []
    if errs:
        raise ShopifyError(f"menuUpdate: {json.dumps(errs, ensure_ascii=False)}")
    return {"menu_handle": menu.get("handle")}


def main() -> int:
    shop, token = sc.load_session()
    coll = sc.find_artist_collection(shop, token, OLD_TITLE)
    if coll is None:
        coll = sc.find_artist_collection(shop, token, NEW_TITLE)
        if coll:
            print(f"[van-gogh] Kolekcja juz ma tytul '{coll.get('title')}' (id={coll.get('id')}).")
            body = coll.get("body_html") or ""
            if OLD_TITLE in body:
                body = body.replace(f'alt="{OLD_TITLE}"', f'alt="{NEW_TITLE}"')
                sc.update_custom_collection(shop, token, int(coll["id"]), body_html=body)
                print("[van-gogh] Poprawiono alt portretu w opisie kolekcji.")
        else:
            print(f"[van-gogh] Nie znaleziono kolekcji «{OLD_TITLE}».", file=sys.stderr)
            return 1
    else:
        updated = rename_collection_title(shop, token, coll, NEW_TITLE)
        body = coll.get("body_html") or ""
        if OLD_TITLE in body:
            body = body.replace(f'alt="{OLD_TITLE}"', f'alt="{NEW_TITLE}"')
            sc.update_custom_collection(shop, token, int(coll["id"]), body_html=body)
        print(
            f"[van-gogh] Kolekcja {coll.get('kind')} id={coll.get('id')}: "
            f"'{OLD_TITLE}' -> '{updated.get('title') or NEW_TITLE}'"
        )

    menu_res = rename_menu_entry(shop, token)
    print(f"[van-gogh] Menu zaktualizowane ({menu_res.get('menu_handle')}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
