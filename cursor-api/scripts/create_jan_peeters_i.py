"""Jednorazowo: utworz artyste «Peeters, Jan I» (kolekcja + opis + menu + produkt)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.create import create_artist_collection_and_menu  # noqa: E402

TITLE = "Peeters, Jan I"
LIFESPAN = "1624 – ok. 1677"
PRODUCT_ID = 15611526873436
DESCRIPTION = """\
Jan Peeters I był flamandzkim malarzem marynistą działającym głównie w Antwerpii w XVII wieku. Związany z tradycją barokowego malarstwa morskiego, specjalizował się w dramatycznych przedstawieniach sztormów, rozbitych okrętów i wybrzeży basenu Morza Śródziemnego — często budując sceny z wyobraźni i wiedzy o statkach, niekoniecznie z własnych podróży.

W jego obrazach morze jest żywiołem bezwzględnym, a galeony — kruche sylwetki walczące z falą. Peeters słynął z precyzyjnego oddawania takielunku, architektury nadmorskich fortyfikacji i teatralnej gry światła w burzowym niebie. Dziś uznawany jest za jednego z ważniejszych flamandzkich marynistów epoki, kontynuatora tradycji malarstwa morskiego rozwijanej w rodzinie Peetersów."""


def main() -> int:
    def log(msg: str) -> None:
        print(msg)

    res = create_artist_collection_and_menu(
        collection_title=TITLE,
        product_ids=[PRODUCT_ID],
        description=DESCRIPTION,
        lifespan=LIFESPAN,
        portrait_path=None,
        logger=log,
    )

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
        f"[peeters] Menu Katalog: "
        f"{'dodano' if menu_res.get('created') else 'juz bylo'}."
    )

    print("\n=== Wynik ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
    if res.get("menu_error"):
        return 2
    if res.get("enrich_error"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
