"""Naprawia handle kolekcji artystow (format: slug('Imie Nazwisko'))."""
from __future__ import annotations

import argparse
import sys
import urllib.parse
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "Komponenty" / "dodajobraz"))

import shopify_client as sc  # noqa: E402
from parser import artist_collection_handle_from_title  # noqa: E402


def is_probable_artist_collection(title: str) -> bool:
    t = (title or "").strip()
    if ", " not in t:
        return False
    left, right = t.split(", ", 1)
    return bool(left.strip() and right.strip() and left[0].isupper())


def iter_custom_collections(shop: str, token: str) -> list[dict]:
    out: list[dict] = []
    base = (
        f"https://{shop}/admin/api/{sc.API_VERSION}/custom_collections.json?"
        + urllib.parse.urlencode({"limit": 250, "fields": "id,title,handle"})
    )
    for batch in sc._paginate_link_header(base, token, list_key="custom_collections"):
        out.extend(batch)
    return out


def collect_mismatches(cols: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for c in cols:
        title = (c.get("title") or "").strip()
        if not is_probable_artist_collection(title):
            continue
        cid = int(c.get("id") or 0)
        cur = (c.get("handle") or "").strip().lower()
        exp = artist_collection_handle_from_title(title)
        if cur != exp:
            rows.append(
                {
                    "id": cid,
                    "title": title,
                    "current": cur,
                    "expected": exp,
                }
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Tylko raport, bez zapisu")
    args = ap.parse_args()

    shop, token = sc.load_session()
    cols = iter_custom_collections(shop, token)
    rows = collect_mismatches(cols)
    if not rows:
        print("Wszystkie handle kolekcji artystow sa poprawne.")
        return 0

    exp_counts: dict[str, int] = {}
    for row in rows:
        exp_counts[row["expected"]] = exp_counts.get(row["expected"], 0) + 1
    dupes = {h: n for h, n in exp_counts.items() if n > 1}
    if dupes:
        print("BLAD: kolizje oczekiwanych handle:")
        for h, n in sorted(dupes.items()):
            print(f"  {h}: {n}x")
        return 2

    print(f"Do naprawy: {len(rows)} kolekcji artystow")
    for row in sorted(rows, key=lambda r: r["title"].lower()):
        print(
            f"{row['id']}\t{row['title']}\t{row['current']} -> {row['expected']}"
        )

    if args.dry_run:
        print("\n(dry-run — bez zmian)")
        return 0

    # Faza 1: unikalne handle tymczasowe (unik kolizji przy zamianie).
    print("\nFaza 1: handle tymczasowe...")
    for row in rows:
        tmp = f"artist-fix-{row['id']}"
        sc.update_custom_collection(shop, token, row["id"], handle=tmp)
        print(f"  {row['id']} -> {tmp}")

    # Faza 2: docelowe handle.
    print("\nFaza 2: docelowe handle...")
    ok = 0
    errors: list[str] = []
    for row in rows:
        try:
            sc.update_custom_collection(
                shop, token, row["id"], handle=row["expected"]
            )
            ok += 1
            print(f"  OK {row['title']} -> {row['expected']}")
        except sc.ShopifyError as e:
            errors.append(f"{row['title']} ({row['id']}): {e}")
            print(f"  BLAD {row['title']}: {e}")

    print(f"\nGotowe: {ok}/{len(rows)}")
    if errors:
        print("Bledy:")
        for err in errors:
            print(f"  - {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
