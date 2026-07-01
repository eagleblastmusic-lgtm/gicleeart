"""Poprawka: «Pośmiertny portret Mosesa ter Borcha» — autor Gesina ter Borch (nie Waterhouse)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.create import build_seo, full_alt_text, preview_alt_text
from Komponenty.dodajobraz.parser import (
    compute_source_key,
    source_key_tag,
)

PRODUCT_ID = 15611530183004
OLD_ARTIST = "John William Waterhouse"
NEW_ARTIST = "Gesina ter Borch"
PAINTING_TITLE = "Pośmiertny portret Mosesa ter Borcha"
OLD_LIFESPAN = "6 Kwi 1849 – 10 Lut 1917"
NEW_LIFESPAN = "15 Lis 1631 – 16 Kwi 1690"
OLD_SRC_TAG = "src:john-william-waterhouse__memorial-portrait-of-moses-ter-borch"
GESINA_COLLECTION_TITLE = "Ter Borch, Gesina"
WATERHOUSE_COLLECTION_TITLE = "Waterhouse, John William"


def _replace_body(body_html: str) -> str:
    out = body_html.replace(OLD_ARTIST, NEW_ARTIST)
    out = out.replace(OLD_LIFESPAN, NEW_LIFESPAN)
    # angielskie daty / autor w szczegółach (gdyby były)
    out = re.sub(
        r"6 Apr 1849\s*[–-]\s*10 Feb 1917",
        NEW_LIFESPAN,
        out,
        flags=re.I,
    )
    return out


def _update_tags(tags_csv: str, *, new_src_tag: str) -> str:
    tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
    kept: list[str] = []
    for t in tags:
        low = t.lower()
        if low.startswith("src:") and "waterhouse" in low and "moses" in low:
            continue
        if t == OLD_SRC_TAG:
            continue
        kept.append(t)
    if new_src_tag not in kept:
        kept.append(new_src_tag)
    if "gesina ter borch" not in {x.lower() for x in kept}:
        kept.append("gesina ter borch")
    return ", ".join(kept)


def _update_image_alt(alt: str) -> str:
    if not alt:
        return alt
    if OLD_ARTIST in alt:
        return alt.replace(OLD_ARTIST, NEW_ARTIST)
    if "Memorial Portrait of Moses Ter Borch" in alt:
        return alt.replace(
            "John William Waterhouse - Memorial Portrait of Moses Ter Borch",
            f"{NEW_ARTIST} - Memorial Portrait of Moses Ter Borch",
        )
    return alt


def main() -> int:
    shop, token = sc.load_session()
    pid = PRODUCT_ID

    prod = sc.get_product(shop, token, pid)
    if not prod.get("id"):
        print(f"Brak produktu id={pid}")
        return 1

    body_html = _replace_body(prod.get("body_html") or "")
    new_title = f"{NEW_ARTIST} - {PAINTING_TITLE}"
    source_key = compute_source_key(NEW_ARTIST, PAINTING_TITLE)
    new_src_tag = source_key_tag(source_key)
    tags = _update_tags(prod.get("tags") or "", new_src_tag=new_src_tag)
    title_tag, meta_desc, handle = build_seo(
        tytul=PAINTING_TITLE,
        artysta=NEW_ARTIST,
        gatunek="",
        nurt="",
    )

    print(f"Nowy tytul: {new_title}")
    print(f"Nowy handle: {handle}")
    print(f"Nowy src tag: {new_src_tag}")

    sc.update_product(
        shop,
        token,
        pid,
        {
            "title": new_title,
            "handle": handle,
            "body_html": body_html,
            "tags": tags,
        },
    )
    print("OK: title, handle, body_html, tags")

    sc.set_seo_metafields(shop, token, pid, title_tag=title_tag, description_tag=meta_desc)
    print("OK: SEO metafields")

    if source_key:
        sc.upsert_metafield(
            shop,
            token,
            pid,
            namespace="custom",
            key="source_key",
            value=source_key,
        )
        print(f"OK: custom.source_key = {source_key}")

    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        alt = _update_image_alt(img.get("alt") or "")
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 2:
            alt = full_alt_text(NEW_ARTIST, PAINTING_TITLE)
        elif "(preview)" in src:
            alt = preview_alt_text(NEW_ARTIST, PAINTING_TITLE)
        elif "(mockup)" in src and alt == _update_image_alt(img.get("alt") or ""):
            alt = f"{NEW_ARTIST} - {PAINTING_TITLE} - (mockup)"
        sc.rest_put(
            shop,
            token,
            f"products/{pid}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )
        print(f"OK: image {img_id} alt")

    ges = sc.find_artist_collection(shop, token, GESINA_COLLECTION_TITLE)
    if ges:
        cid = int(ges["id"])
        if not sc.is_product_in_collection(shop, token, pid, cid, collection_kind="custom"):
            sc.add_to_collect(shop, token, pid, cid)
            print(f"OK: dodano do kolekcji «{GESINA_COLLECTION_TITLE}»")
        else:
            print(f"Juz w kolekcji «{GESINA_COLLECTION_TITLE}»")
    else:
        print(f"UWAGA: brak kolekcji «{GESINA_COLLECTION_TITLE}»")

    wh = sc.find_artist_collection(shop, token, WATERHOUSE_COLLECTION_TITLE)
    if wh:
        cid = int(wh["id"])
        if sc.is_product_in_collection(shop, token, pid, cid, collection_kind="custom"):
            out = sc.rest_get(
                shop,
                token,
                "collects.json",
                product_id=pid,
                limit=250,
            )
            for col in out.get("collects") or []:
                if int(col.get("collection_id") or 0) != cid:
                    continue
                if int(col.get("product_id") or 0) != pid:
                    continue
                sc.delete_collect(shop, token, int(col["id"]))
                print(f"OK: usunieto z kolekcji Waterhouse (collect {col['id']})")

    print(f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
