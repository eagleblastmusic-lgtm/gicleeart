"""Audit artist collection handles vs expected slug."""
from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DODAJ = _ROOT / "Komponenty" / "dodajobraz"
sys.path.insert(0, str(_DODAJ))

import shopify_client as sc  # noqa: E402
from parser import artist_collection_handle_from_title  # noqa: E402


def is_probable_artist_collection(title: str) -> bool:
    t = (title or "").strip()
    if ", " not in t:
        return False
    left, right = t.split(", ", 1)
    return bool(left.strip() and right.strip() and left[0].isupper())


def expected_handle(title: str) -> str:
    return artist_collection_handle_from_title(title)


def iter_custom_collections(shop: str, token: str) -> list[dict]:
    out: list[dict] = []
    base = (
        f"https://{shop}/admin/api/{sc.API_VERSION}/custom_collections.json?"
        + urllib.parse.urlencode({"limit": 250, "fields": "id,title,handle"})
    )
    for batch in sc._paginate_link_header(base, token, list_key="custom_collections"):
        out.extend(batch)
    return out


def main() -> int:
    shop, token = sc.load_session()
    cols = iter_custom_collections(shop, token)
    bad: list[tuple[str, str, str, int]] = []
    ok = 0
    for c in cols:
        title = (c.get("title") or "").strip()
        if not is_probable_artist_collection(title):
            continue
        exp = expected_handle(title)
        cur = (c.get("handle") or "").strip().lower()
        cid = int(c.get("id") or 0)
        if cur == exp:
            ok += 1
        else:
            bad.append((title, cur, exp, cid))
    print(f"OK: {ok}, mismatched: {len(bad)}")
    for title, cur, exp, cid in sorted(bad, key=lambda x: x[0].lower()):
        print(f"{cid}\t{title}\t{cur}\t->\t{exp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
