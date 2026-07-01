"""Masowa zmiana wartości opcji Rozmiar: S → M we wszystkich produktach Shopify.

Używa GraphQL `productOptionUpdate` (optionValuesToUpdate) — aktualizuje wartość
opcji i powiązane warianty w jednym kroku.

Uruchomienie (z folderu cursor-api):

    # Podgląd — bez zapisu
    python -m scripts.rename_size_s_to_m

    # Wykonaj zmiany
    python -m scripts.rename_size_s_to_m --apply

    # Jeden produkt (test)
    python -m scripts.rename_size_s_to_m --apply --product-id 15524677845340

    # Wszystkie produkty (bez filtra vendor)
    python -m scripts.rename_size_s_to_m --apply --all-vendors

Po migracji warto uruchomić backfill tłumaczeń opcji (M jest pass-through, ale
odświeża wpisy Translations API):

    python -m scripts.backfill_option_translations

Wymagania:
    - `.shopify_session.json` (po `npm run oauth` w cursor-api)
    - scope: `read_products`, `write_products`
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
from Komponenty.dodajobraz.shopify_client import ShopifyError  # noqa: E402

OLD_SIZE = "S"
NEW_SIZE = "M"
DEFAULT_VENDOR = "Giclee Art"
DEFAULT_PRODUCT_TYPE = "Obraz"

_SIZE_OPTION_HINTS = ("rozmiar", "size", "wymiar", "format")

_RENAME_MUTATION = """
mutation RenameSizeOptionValue(
  $productId: ID!,
  $option: OptionUpdateInput!,
  $optionValuesToUpdate: [OptionValueUpdateInput!]
) {
  productOptionUpdate(
    productId: $productId
    option: $option
    optionValuesToUpdate: $optionValuesToUpdate
  ) {
    userErrors { field message code }
    product { id title }
  }
}
"""


def _log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = msg.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe, flush=True)


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


def _is_size_option_name(name: str) -> bool:
    n = _norm(name)
    return any(h in n for h in _SIZE_OPTION_HINTS)


def _find_size_value_s(options: list[dict]) -> tuple[str, str, str] | None:
    """Zwraca (option_gid, value_gid, option_name) gdy jest wartość S w opcji rozmiaru."""
    for opt in options:
        opt_name = str(opt.get("name") or "")
        if not _is_size_option_name(opt_name):
            continue
        opt_gid = str(opt.get("id") or "").strip()
        if not opt_gid:
            continue
        values = opt.get("values") or []
        has_m = any(_norm(v.get("name") or "") == _norm(NEW_SIZE) for v in values)
        for val in values:
            if _norm(val.get("name") or "") != _norm(OLD_SIZE):
                continue
            val_gid = str(val.get("id") or "").strip()
            if not val_gid:
                continue
            if has_m:
                return ("__CONFLICT__", val_gid, opt_name)
            return (opt_gid, val_gid, opt_name)
    return None


def rename_size_on_product(
    shop: str,
    token: str,
    product_id: int,
    *,
    apply: bool,
) -> str:
    """Zwraca status: ok | skipped | conflict | error."""
    gid = sc.product_gid(product_id)
    options = sc.get_product_options_with_gids(shop, token, gid)
    found = _find_size_value_s(options)
    if not found:
        return "skipped"
    opt_gid, val_gid, opt_name = found
    if opt_gid == "__CONFLICT__":
        return "conflict"

    if not apply:
        return "ok"

    variables = {
        "productId": gid,
        "option": {"id": opt_gid},
        "optionValuesToUpdate": [{"id": val_gid, "name": NEW_SIZE}],
    }
    data = sc.graphql(shop, token, _RENAME_MUTATION, variables)
    payload = (data or {}).get("productOptionUpdate") or {}
    errors = payload.get("userErrors") or []
    if errors:
        raise ShopifyError(f"productOptionUpdate userErrors: {errors}")
    return "ok"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Zmiana opcji Rozmiar S → M w Shopify.")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Wykonaj zmiany (domyślnie tylko podgląd).",
    )
    p.add_argument(
        "--product-id",
        type=int,
        default=0,
        help="Tylko ten produkt (ID numeryczne Shopify).",
    )
    p.add_argument(
        "--vendor",
        default=DEFAULT_VENDOR,
        help=f"Filtr vendor (domyślnie: {DEFAULT_VENDOR!r}).",
    )
    p.add_argument(
        "--product-type",
        default=DEFAULT_PRODUCT_TYPE,
        help=f"Filtr product_type (domyślnie: {DEFAULT_PRODUCT_TYPE!r}).",
    )
    p.add_argument(
        "--all-vendors",
        action="store_true",
        help="Pomiń filtr vendor (wszystkie produkty danego typu).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    started = datetime.now()
    mode = "APPLY" if args.apply else "DRY-RUN"
    _log(f"[rename S->M] START {started.isoformat(timespec='seconds')} ({mode})")

    shop, token = sc.load_session()
    _log(f"[rename S->M] Sklep: {shop}")

    if args.product_id:
        products = [{"id": args.product_id, "title": f"#{args.product_id}"}]
    else:
        products = sc.iter_all_products(
            shop,
            token,
            product_type=args.product_type or None,
            fields="id,title,handle,vendor,product_type,options",
        )
        if not args.all_vendors and args.vendor:
            vendor_key = _norm(args.vendor)
            products = [
                p
                for p in products
                if _norm(p.get("vendor") or "") == vendor_key
            ]

    # Szybki filtr REST — opcja Rozmiar z wartością S (mniej wywołań GraphQL).
    candidates: list[dict] = []
    for p in products:
        opts = p.get("options") or []
        has_s = False
        for opt in opts:
            if not _is_size_option_name(str(opt.get("name") or "")):
                continue
            vals = opt.get("values") or []
            if isinstance(vals, list) and any(_norm(v) == _norm(OLD_SIZE) for v in vals):
                has_s = True
                break
        if has_s:
            candidates.append(p)

    total = len(candidates)
    _log(f"[rename S->M] Produktów z opcją {OLD_SIZE!r}: {total} (z {len(products)} w katalogu)")
    if not candidates:
        _log("[rename S->M] Nic do zrobienia.")
        return 0

    ok = skipped = conflict = failed = 0

    for i, p in enumerate(candidates, start=1):
        pid = int(p["id"])
        title = (p.get("title") or "").strip()
        _log(f"[{i}/{total}] {pid} — {title}")
        try:
            status = rename_size_on_product(shop, token, pid, apply=args.apply)
        except ShopifyError as e:
            failed += 1
            _log(f"  ERROR: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            failed += 1
            _log(f"  ERROR: {e}")
            continue

        if status == "ok":
            ok += 1
            suffix = "-> zapisano M" if args.apply else "-> do zmiany (dry-run)"
            _log(f"  OK {suffix}")
        elif status == "skipped":
            skipped += 1
            _log("  SKIP (brak S w GraphQL — może już M)")
        elif status == "conflict":
            conflict += 1
            _log(f"  CONFLICT — produkt ma już {NEW_SIZE!r} i {OLD_SIZE!r}; wymaga ręcznej korekty")
        else:
            skipped += 1
            _log(f"  SKIP ({status})")

    elapsed = datetime.now() - started
    _log(
        f"[rename S->M] KONIEC — ok={ok}, skipped={skipped}, conflict={conflict}, "
        f"failed={failed}, czas={elapsed}"
    )
    if not args.apply and ok:
        _log("[rename S->M] Uruchom ponownie z --apply, aby zapisać zmiany.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
