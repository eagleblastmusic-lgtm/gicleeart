"""Backfill tlumaczen body_html (sekcja 'SZCZEGOLY' w jezyku docelowym)
dla istniejacych produktow w sklepie.

Cel:
  Stara wersja `dodajobraz` wysylala body_html w jezykach obcych z polskim
  naglowkiem 'SZCZEGOLY' i polskimi etykietami pol oraz wartosciami
  faktograficznymi po polsku (Olej na plotnie / Pejzaz marynistyczny / XIX wiek).
  Po refactorze etykiety i wartosci sa lokalizowane (body_i18n.py).

  Ten skrypt POBIERA istniejaca tlumaczona wersje body_html z Shopify
  (Translations API), parsuje z niej polski naglowek/etykiety i podmienia je
  na lokalizowane odpowiedniki + tlumaczy najczestsze wartosci faktograficzne
  ze slownika `body_i18n.COMMON_VALUE_TRANSLATIONS`. NIE zmienia trzech akapitow
  opisu (te juz sa po obcemu z poprzedniego pushu LLM).

Uruchomienie:
    cd cursor-api
    python -m scripts.backfill_body_translations               # pisze
    python -m scripts.backfill_body_translations --dry-run      # tylko diagnostyka

Wymagania:
    - .shopify_session.json (po `npm run oauth`)
    - scope: read_products + read_translations + write_translations
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
_CURSOR_API = _THIS.parent.parent
if str(_CURSOR_API) not in sys.path:
    sys.path.insert(0, str(_CURSOR_API))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402
from Komponenty.dodajobraz.body_i18n import (  # noqa: E402
    BODY_LABELS_I18N,
    SUPPORTED_LANGS,
    body_labels,
    translate_field_value_or_pl,
)

VENDOR = "Giclee Art"
PRODUCT_TYPE = "Obraz"

PL_LABELS = BODY_LABELS_I18N["pl"]


def _log(msg: str) -> None:
    print(msg, flush=True)


# Regex do podmiany etykiet PL na docelowe (kazda etykieta zaczyna sie '<strong>...:')
def _replace_label(html: str, pl_label: str, target_label: str) -> str:
    """Zamienia np. '<strong>Tytul: ' na '<strong>Title: '. Idempotentne."""
    pattern = re.compile(re.escape(f"<strong>{pl_label}:") , re.IGNORECASE)
    return pattern.sub(f"<strong>{target_label}:", html)


def _replace_value_after_label(html: str, label: str, lang: str) -> str:
    """Po etykiecie '<strong>{label}: </strong>' znajduje wartosc do najblizszego '<br>'
    lub konca komorki ('</td>') i tlumaczy ja przez body_i18n."""
    label_esc = re.escape(label)
    pat = re.compile(rf"(<strong>{label_esc}:\s*</strong>\s*)([^<]+?)(<br>|</td>)", re.IGNORECASE)

    def _repl(m: re.Match) -> str:
        head, value, tail = m.group(1), m.group(2), m.group(3)
        translated = translate_field_value_or_pl(value.strip(), lang)
        return f"{head}{translated}{tail}"

    return pat.sub(_repl, html)


def _localize_html(html_pl_overlay: str, lang: str) -> str:
    """Bierze body_html ktory zostal pushniety jako tlumaczenie (akapity juz sa
    obcojezyczne, ale naglowek + etykiety + wartosci wciaz po polsku) i podmienia
    naglowek/etykiety/wartosci na lokalizowane.

    Idempotentne: jesli juz raz przeszlo - drugi raz nic nie zmienia (regexy na
    polskich literach nie dopasuja).
    """
    target = body_labels(lang)
    html = html_pl_overlay

    # 1) Naglowek "SZCZEGOLY"
    html = html.replace(f"<strong>{PL_LABELS['header']}</strong>",
                        f"<strong>{target['header']}</strong>")

    # 2) Etykiety pol PL -> docelowe
    pairs = [
        ("tytul_orig", PL_LABELS["tytul_orig"], target["tytul_orig"]),
        ("tytul",      PL_LABELS["tytul"],      target["tytul"]),
        ("autor",      PL_LABELS["autor"],      target["autor"]),
        ("data",       PL_LABELS["data_powstania"], target["data_powstania"]),
        ("miejsce",    PL_LABELS["miejsce_powstania"], target["miejsce_powstania"]),
        ("typ",        PL_LABELS["typ"],        target["typ"]),
        ("technika",   PL_LABELS["technika"],   target["technika"]),
        ("gatunek",    PL_LABELS["gatunek"],    target["gatunek"]),
        ("nurt",       PL_LABELS["nurt"],       target["nurt"]),
        ("forma",      PL_LABELS["forma"],      target["forma"]),
    ]
    # Kolejnosc wazna: 'tytul_orig' (Tytul oryginalny) PRZED 'tytul' zeby nie
    # zostac przedwczesnie podmienionym przez krotszy 'Tytul'.
    for _, pl_lbl, target_lbl in pairs:
        html = _replace_label(html, pl_lbl, target_lbl)

    # 3) Wartosc pola "Typ" - hardcoded "Obraz" -> lokalizowane (Tableau/Painting/...)
    html = re.sub(
        rf"(<strong>{re.escape(target['typ'])}\s*:\s*</strong>\s*)Obraz",
        rf"\g<1>{target['typ_value']}",
        html,
    )

    # 4) Tlumacz wartosci faktograficzne pod etykietami (technika/gatunek/nurt/
    #    forma/data/miejsce_powstania/tytul_orig - tytul i autor zostaja).
    for label_key in (
        "data_powstania", "miejsce_powstania",
        "technika", "gatunek", "nurt", "forma",
    ):
        html = _replace_value_after_label(html, target[label_key], lang)

    return html


def _get_translation_html(shop: str, token: str, product_gid: str, lang: str) -> str | None:
    """Czyta `body_html` przetlumaczony dla danego locale (jezeli istnieje).

    Uzywa GraphQL `translatableResource(resourceId).translations(locale)` i wyciaga
    tlumaczenie pola 'body_html'.
    """
    query = """
    query($id: ID!, $locale: String!) {
      translatableResource(resourceId: $id) {
        translations(locale: $locale) { key value }
      }
    }
    """
    data = sc.graphql(shop, token, query, {"id": product_gid, "locale": lang})
    res = (data or {}).get("translatableResource") or {}
    for t in (res.get("translations") or []):
        if (t or {}).get("key") == "body_html":
            return (t.get("value") or "")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Nic nie zapisuje, tylko raportuje co by zmienilo.")
    args = parser.parse_args(argv)

    started = datetime.now()
    _log(f"[backfill-body] START {started.isoformat(timespec='seconds')}")
    _log(f"[backfill-body] Jezyki: {list(SUPPORTED_LANGS)} dry_run={args.dry_run}")

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
    _log(f"[backfill-body] Produktow: {total}")

    ok = 0
    failed = 0
    skipped_lang = 0
    errors_summary: list[dict] = []

    for i, p in enumerate(products, start=1):
        pid = int(p.get("id"))
        gid = sc.product_gid(pid)
        _log(f"[{i}/{total}] {pid} - {(p.get('title') or '').strip()}")

        for lang in SUPPORTED_LANGS:
            current = _get_translation_html(shop, token, gid, lang)
            if not current:
                skipped_lang += 1
                continue
            new_html = _localize_html(current, lang)
            if new_html == current:
                _log(f"    [{lang}] bez zmian (juz lokalizowane lub brak polskich etykiet w overlayu).")
                continue
            if args.dry_run:
                _log(f"    [{lang}] DRY-RUN: zaplanowano podmiane (rozmiar staly).")
                continue
            try:
                sc.register_translations(
                    shop, token,
                    resource_gid=gid,
                    locale=lang,
                    fields={"body_html": new_html},
                )
                _log(f"    [{lang}] OK - body_html zaktualizowany.")
            except sc.ShopifyError as e:
                failed += 1
                errors_summary.append({"pid": pid, "lang": lang, "error": str(e)})
                _log(f"    [{lang}] BLAD: {e}")

        ok += 1

    finished = datetime.now()
    _log("=" * 60)
    _log(f"[backfill-body] KONIEC {finished.isoformat(timespec='seconds')} "
         f"(czas: {(finished - started).total_seconds():.1f}s)")
    _log(f"[backfill-body] Produkty przetworzone: {ok}")
    _log(f"[backfill-body] Bledy:                  {failed}")
    _log(f"[backfill-body] Skipped (brak translacji body_html dla lang): {skipped_lang}")
    if errors_summary:
        _log("[backfill-body] Szczegoly bledow:")
        for er in errors_summary[:25]:
            _log(f"  - id={er['pid']} {er['lang']} -> {er['error']}")
        if len(errors_summary) > 25:
            _log(f"  ... +{len(errors_summary) - 25} wiecej")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
