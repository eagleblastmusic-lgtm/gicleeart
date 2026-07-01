"""Poprawka: «Statki w sztormie» — autor Ludolf Bakhuizen (nie Ivan Aivazovsky)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
from Komponenty.dodajobraz.create import build_seo, full_alt_text, preview_alt_text
from Komponenty.dodajobraz.description_update import get_translated_fields
from Komponenty.dodajobraz.parser import compute_source_key, source_key_tag

PRODUCT_ID = 15549062414684
OLD_ARTIST = "Ivan Aivazovsky"
NEW_ARTIST = "Ludolf Bakhuizen"
PL_TITLE = (
    "Statki podczas sztormu u skalistego wybrzeża "
    "(lub Okręty w czasie burzy na morzu przy brzegu)"
)
ALT_EN = "Ships in a Tempest off a Rocky Coast"
OLD_LIFESPAN = "29 Lip 1817 – 2 Maj 1900"
NEW_LIFESPAN = "28 Gru 1630 – 17 Lis 1708"
OLD_SRC_TAG = "src:ivan-aivazovsky__ships-in-a-tempest"
AIVAZOVSKY_COLLECTION = "Aivazovsky, Ivan"
BAKHUIZEN_COLLECTION = "Bakhuizen, Ludolf"


def _replace_body(body_html: str) -> str:
    out = body_html.replace(OLD_ARTIST, NEW_ARTIST)
    out = out.replace(OLD_LIFESPAN, NEW_LIFESPAN)
    out = re.sub(
        r"29 Jul 1817\s*[–-]\s*2 May 1900",
        "28 Dec 1630 – 17 Nov 1708",
        out,
        flags=re.I,
    )
    return out


def _update_tags(tags_csv: str, *, new_src_tag: str) -> str:
    tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
    kept: list[str] = []
    for t in tags:
        low = t.lower()
        if low == OLD_SRC_TAG:
            continue
        if low.startswith("src:") and "aivazovsky" in low:
            continue
        if low in ("ivan aivazovsky", "aivazovsky", "ajwazowski"):
            continue
        kept.append(t)
    for add in (new_src_tag, "ludolf bakhuizen", "bakhuizen"):
        if add not in {x.lower() for x in kept}:
            kept.append(add)
    return ", ".join(kept)


def main() -> int:
    shop, token = sc.load_session()
    pid = PRODUCT_ID
    gid = sc.product_gid(pid)

    prod = sc.get_product(shop, token, pid)
    if not prod.get("id"):
        print(f"Brak produktu id={pid}")
        return 1

    body_html = _replace_body(prod.get("body_html") or "")
    new_product_title = f"{NEW_ARTIST} - {PL_TITLE}"
    source_key = compute_source_key(NEW_ARTIST, ALT_EN)
    new_src_tag = source_key_tag(source_key)
    tags = _update_tags(prod.get("tags") or "", new_src_tag=new_src_tag)
    title_tag, meta_desc, handle = build_seo(
        tytul=PL_TITLE,
        artysta=NEW_ARTIST,
        gatunek="",
        nurt="",
    )

    print(f"Nowy tytul: {new_product_title}")
    print(f"Nowy handle: {handle}")
    print(f"Nowy src tag: {new_src_tag}")

    sc.update_product(
        shop,
        token,
        pid,
        {
            "title": new_product_title,
            "handle": handle,
            "body_html": body_html,
            "tags": tags,
        },
    )
    sc.set_seo_metafields(shop, token, pid, title_tag=title_tag, description_tag=meta_desc)

    if source_key:
        sc.upsert_metafield(
            shop, token, pid,
            namespace="custom", key="source_key", value=source_key,
        )

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            continue
        updated = _replace_body(body)
        if updated != body:
            sc.register_translations(
                shop, token, resource_gid=gid, locale=loc, fields={"body_html": updated},
            )
            print(f"OK: body_html {loc} — zamiana artysty")

    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(NEW_ARTIST, ALT_EN)
        elif "(preview)" in src:
            alt = preview_alt_text(NEW_ARTIST, ALT_EN)
        elif "(mockup)" in src:
            alt = f"{NEW_ARTIST} - {ALT_EN} - (mockup)"
        else:
            alt = f"{NEW_ARTIST} - {ALT_EN}"
        sc.rest_put(
            shop,
            token,
            f"products/{pid}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )

    bak = sc.find_artist_collection(shop, token, BAKHUIZEN_COLLECTION)
    if bak:
        cid = int(bak["id"])
        if not sc.is_product_in_collection(shop, token, pid, cid, collection_kind="custom"):
            sc.add_to_collect(shop, token, pid, cid)
            print(f"OK: dodano do «{BAKHUIZEN_COLLECTION}»")

    aiv = sc.find_artist_collection(shop, token, AIVAZOVSKY_COLLECTION)
    if aiv:
        cid = int(aiv["id"])
        if sc.is_product_in_collection(shop, token, pid, cid, collection_kind="custom"):
            out = sc.rest_get(shop, token, "collects.json", product_id=pid, limit=250)
            for col in out.get("collects") or []:
                if int(col.get("collection_id") or 0) == cid:
                    sc.delete_collect(shop, token, int(col["id"]))
                    print(f"OK: usunieto z «{AIVAZOVSKY_COLLECTION}»")

    print(f"\nAdmin: https://admin.shopify.com/store/{shop.split('.')[0]}/products/{pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
