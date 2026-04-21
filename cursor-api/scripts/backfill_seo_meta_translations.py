"""Backfill tlumaczen SEO (meta_title / meta_description) na zasobie Product
dla istniejacych produktow w sklepie.

Tlo:
  Stara wersja `dodajobraz` zapisywala tlumaczenia SEO na metafieldach
  `global.title_tag` / `global.description_tag` - to nie dziala w Shopify
  Translations API. Aplikacja Translate & Adapt czyta wlasnie pola
  `meta_title` / `meta_description` na zasobie Product.

Strategia tego skryptu (BEZ LLM):
  1. Czyta polskie SEO (z metafieldow `global.title_tag` / `global.description_tag`
     na produkcie - to jest baza), bo na nim zostalo zapisane przez stary kod.
  2. NIE zna jeszcze przetlumaczonych SEO (te sa wytwarzane przez LLM przy
     publikacji). Wiec dla istniejacych produktow tymczasowo *kopiuje polskie*
     SEO jako fallback we wszystkich 6 jezykach (lepsze niz puste pole - przy
     nastepnej re-publikacji aplikacja nadpisze prawidlowymi tlumaczeniami).

  Jesli wolisz puste pola SEO niz polski fallback - uruchom z flag
  --no-fallback (skrypt wtedy tylko zaraportuje braki, nic nie wpisze).

Uruchomienie:
    cd cursor-api
    python -m scripts.backfill_seo_meta_translations             # z fallbackiem PL
    python -m scripts.backfill_seo_meta_translations --no-fallback   # tylko raport

Wymagania:
    - .shopify_session.json (po `npm run oauth`)
    - scope: read_products + write_translations + read_translations
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
_CURSOR_API = _THIS.parent.parent
if str(_CURSOR_API) not in sys.path:
    sys.path.insert(0, str(_CURSOR_API))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.options_i18n import SUPPORTED_LANGS  # noqa: E402

VENDOR = "Giclee Art"
PRODUCT_TYPE = "Obraz"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _read_pl_seo(shop: str, token: str, product_id: int) -> tuple[str, str]:
    """Zwraca (title_tag, description_tag) z metafieldow global.* (PL)."""
    title_tag = ""
    description_tag = ""
    mt = sc.find_metafield(shop, token, product_id, namespace="global", key="title_tag")
    if mt:
        title_tag = (mt.get("value") or "").strip()
    md = sc.find_metafield(shop, token, product_id, namespace="global", key="description_tag")
    if md:
        description_tag = (md.get("value") or "").strip()
    return title_tag, description_tag


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Nie wpisuj polskiego SEO jako fallbacku - tylko zaraportuj braki.",
    )
    args = parser.parse_args(argv)

    started = datetime.now()
    _log(f"[backfill-seo] START {started.isoformat(timespec='seconds')}")
    _log(f"[backfill-seo] Jezyki: {list(SUPPORTED_LANGS)}, "
         f"fallback PL: {'NIE' if args.no_fallback else 'TAK'}")

    shop, token = sc.load_session()
    products = sc.iter_all_products(
        shop, token,
        product_type=PRODUCT_TYPE,
        fields="id,title,handle,vendor,product_type",
    )
    products = [
        p for p in products
        if (p.get("vendor") or "").strip().lower() == VENDOR.lower()
    ]
    total = len(products)
    _log(f"[backfill-seo] Produktow: {total}")

    ok = 0
    failed = 0
    no_seo = 0
    errors_summary: list[dict] = []

    for i, p in enumerate(products, start=1):
        pid = int(p.get("id"))
        title = (p.get("title") or "").strip()
        gid = sc.product_gid(pid)
        _log(f"[{i}/{total}] {pid} - {title}")

        title_pl, desc_pl = _read_pl_seo(shop, token, pid)
        if not title_pl and not desc_pl:
            no_seo += 1
            _log("    -> brak SEO PL na metafieldach global.* (pomijam).")
            continue

        if args.no_fallback:
            _log(f"    -> SEO PL OK (title={bool(title_pl)}, desc={bool(desc_pl)}) - tryb raportowy, nic nie pisze.")
            continue

        any_err = False
        for lang in SUPPORTED_LANGS:
            fields: dict[str, str] = {}
            if title_pl:
                fields["meta_title"] = title_pl
            if desc_pl:
                fields["meta_description"] = desc_pl
            if not fields:
                continue
            try:
                sc.register_translations(
                    shop, token,
                    resource_gid=gid,
                    locale=lang,
                    fields=fields,
                )
            except sc.ShopifyError as e:
                any_err = True
                errors_summary.append({"product_id": pid, "lang": lang, "error": str(e)})
                _log(f"    -> {lang} BLAD: {e}")

        if any_err:
            failed += 1
        else:
            ok += 1
            _log(f"    -> OK ({len(SUPPORTED_LANGS)} jezykow zapisanych jako fallback PL)")

    finished = datetime.now()
    _log("=" * 60)
    _log(f"[backfill-seo] KONIEC {finished.isoformat(timespec='seconds')} "
         f"(czas: {(finished - started).total_seconds():.1f}s)")
    _log(f"[backfill-seo] OK:           {ok}")
    _log(f"[backfill-seo] BLEDY:        {failed}")
    _log(f"[backfill-seo] BEZ SEO PL:   {no_seo}")
    if errors_summary:
        _log("[backfill-seo] Szczegoly bledow:")
        for er in errors_summary[:25]:
            _log(f"  - id={er['product_id']} {er['lang']} -> {er['error']}")
        if len(errors_summary) > 25:
            _log(f"  ... +{len(errors_summary) - 25} wiecej")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
