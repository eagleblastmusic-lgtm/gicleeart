"""Backfill tlumaczen opcji wariantow (Kolor / Rozmiar / Rodzaj drewna i ich
wartosci) na 6 jezykow obcych dla wszystkich istniejacych produktow w sklepie.

Uzywa statycznego slownika z `Komponenty.dodajobraz.options_i18n` - bez LLM,
deterministycznie. Bezpieczne do wielokrotnego uruchamiania (idempotentne -
Shopify Translations API nadpisuje istniejace wpisy o tym samym key/locale).

UWAGA: skrypt NIE backfilluje SEO meta_title / meta_description (te wymagaja
oryginalnych tlumaczen z LLM-a; uzupelnia sie je przy nastepnej re-publikacji
produktu z `dodajobraz`).

Uruchomienie:
    cd cursor-api
    python -m scripts.backfill_option_translations

Wymagania:
    - .shopify_session.json (po `npm run oauth`)
    - scope: read_products + write_translations + read_translations
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Wstrzykujemy katalog 'cursor-api' do sys.path, zeby dzialalo wywolanie
# `python scripts/backfill_option_translations.py` (poza trybem -m).
_THIS = Path(__file__).resolve()
_CURSOR_API = _THIS.parent.parent
if str(_CURSOR_API) not in sys.path:
    sys.path.insert(0, str(_CURSOR_API))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.create import push_option_translations  # noqa: E402
from Komponenty.dodajobraz.options_i18n import SUPPORTED_LANGS  # noqa: E402

VENDOR = "Giclee Art"
PRODUCT_TYPE = "Obraz"


def _log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = msg.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe, flush=True)


def main() -> int:
    started = datetime.now()
    _log(f"[backfill] START {started.isoformat(timespec='seconds')}")
    _log(f"[backfill] Jezyki docelowe: {list(SUPPORTED_LANGS)}")

    shop, token = sc.load_session()
    _log(f"[backfill] Sklep: {shop}")

    products = sc.iter_all_products(
        shop, token,
        product_type=PRODUCT_TYPE,
        fields="id,title,handle,vendor,product_type,options",
    )
    # Filtrujemy po vendor (Shopify REST nie ma filtra `vendor` w iter_all_products,
    # wiec robimy to po stronie klienta).
    products = [
        p for p in products
        if (p.get("vendor") or "").strip().lower() == VENDOR.lower()
    ]
    total = len(products)
    _log(f"[backfill] Produktow do przetworzenia: {total}")
    if not products:
        _log("[backfill] Brak produktow - koniec.")
        return 0

    ok = 0
    failed = 0
    skipped = 0
    errors_summary: list[dict] = []

    for i, p in enumerate(products, start=1):
        pid = int(p.get("id"))
        title = (p.get("title") or "").strip()
        product_gid_str = sc.product_gid(pid)
        _log(f"[{i}/{total}] {pid} - {title}")

        options = p.get("options") or []
        if not options:
            _log("    -> brak opcji wariantow, pomijam.")
            skipped += 1
            continue

        try:
            summary = push_option_translations(
                product_gid=product_gid_str,
                languages=list(SUPPORTED_LANGS),
                logger=_log,
            )
            errs = summary.get("errors") or []
            if errs:
                failed += 1
                errors_summary.append({"product_id": pid, "title": title, "errors": errs})
                _log(f"    -> czesciowy sukces, bledy: {len(errs)}")
            else:
                ok += 1
                _log("    -> OK")
        except Exception as e:
            failed += 1
            errors_summary.append({"product_id": pid, "title": title, "errors": [str(e)]})
            _log(f"    -> BLAD: {e}")

    finished = datetime.now()
    _log("=" * 60)
    _log(f"[backfill] KONIEC {finished.isoformat(timespec='seconds')} "
         f"(czas: {(finished - started).total_seconds():.1f}s)")
    _log(f"[backfill] OK:        {ok}")
    _log(f"[backfill] BLEDY:     {failed}")
    _log(f"[backfill] POMINIETE: {skipped}")
    if errors_summary:
        _log("[backfill] Szczegoly bledow:")
        for er in errors_summary[:25]:
            _log(f"  - id={er['product_id']} '{er['title']}' -> {er['errors']}")
        if len(errors_summary) > 25:
            _log(f"  ... +{len(errors_summary) - 25} wiecej")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
