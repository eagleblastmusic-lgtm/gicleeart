"""Jednorazowo: utworz artyste «Van Gogh, Vincent» (kolekcja + opis + portret + menu)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.create import create_artist_collection_and_menu  # noqa: E402

TITLE = "Van Gogh, Vincent"
LIFESPAN = "30 Mar 1853 – 29 Lip 1890"
PORTRAIT_URL = (
    "https://cdn.shopify.com/s/files/1/1011/0517/2828/files/"
    "Vincent_van_Gogh_-_s0273V1962_-_Van_Gogh_Museum.jpg?v=1775141009"
)
DESCRIPTION = """\
Vincent van Gogh był holenderskim malarzem postimpresjonistycznym, którego fascynowała natura, światło i emocje wyrażane przez kolor. Jego obrazy, pełne wirujących linii i intensywnych barw, przedstawiają pola, wierzby, słoneczniki czy nocne niebo, oddając zarówno piękno przyrody, jak i wewnętrzne przeżycia artysty. Van Gogh malował z pasją i spontanicznością, co nadaje jego dziełom wyjątkową ekspresję i siłę emocji.

Artysta studiował w Holandii i Francji, w tym w Paryżu i Arles, gdzie zetknął się z impresjonizmem i sztuką japońską. Tworzył obrazy olejne i rysunki, łącząc intensywne kolory z fakturą farby i dynamicznymi pociągnięciami pędzla. Jego prace przyciągają uwagę siłą ekspresji, głębią nastroju i unikalnym sposobem widzenia świata, pełnym życia i emocji."""


def _fetch_product_ids_by_tag(tag: str) -> list[int]:
    shop, token = sc.load_session()
    safe = tag.replace("\\", "\\\\").replace('"', '\\"')
    q = f'tag:"{safe}"'
    query = """
    query($q: String!, $first: Int!, $after: String) {
      products(first: $first, query: $q, after: $after) {
        pageInfo { hasNextPage endCursor }
        edges { node { legacyResourceId } }
      }
    }
    """
    after: str | None = None
    ids: list[int] = []
    while True:
        data = sc.graphql(shop, token, query, {"q": q, "first": 100, "after": after})
        block = (data or {}).get("products") or {}
        for edge in block.get("edges") or []:
            node = (edge or {}).get("node") or {}
            try:
                ids.append(int(node["legacyResourceId"]))
            except (KeyError, TypeError, ValueError):
                continue
        page_info = block.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
    return ids


def main() -> int:
    def log(msg: str) -> None:
        print(msg)

    product_ids = _fetch_product_ids_by_tag("vincent van gogh")
    log(f"[van-gogh] Znaleziono {len(product_ids)} produkt(ow) z tagiem «vincent van gogh».")

    res = create_artist_collection_and_menu(
        collection_title=TITLE,
        product_ids=product_ids,
        description=DESCRIPTION,
        lifespan=LIFESPAN,
        portrait_url=PORTRAIT_URL,
        logger=log,
    )
    # Nawigacja galerii (coverflow) czyta autorow z podmenu Katalog.
    shop, token = sc.load_session()
    menu_res = sc.add_menu_child_collection(
        shop,
        token,
        parent_title="Katalog",
        child_title=TITLE,
        collection_gid=sc.collection_gid(int(res["collection_id"])),
        menu_handle="main-menu",
    )
    log(
        f"[van-gogh] Menu Katalog: "
        f"{'dodano' if menu_res.get('created') else 'juz bylo'}."
    )
    print("\n=== Wynik ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
    return 0 if not res.get("enrich_error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
