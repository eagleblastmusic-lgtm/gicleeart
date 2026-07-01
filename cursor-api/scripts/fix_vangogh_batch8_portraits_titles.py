"""Poprawka tytulow: 7 produktow Van Gogh — autoportrety i aleja topoli (batch 8)."""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
from Komponenty.dodajobraz.create import build_seo, full_alt_text, preview_alt_text
from Komponenty.dodajobraz.description_update import get_translated_fields
from Komponenty.dodajobraz.html_template import (
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
)

ARTIST = "Vincent Van Gogh"


class ProductTitles(TypedDict):
    product_id: int
    label: str
    old_pl_titles: tuple[str, ...]
    new_pl_title: str
    original_title: str
    english_title: str
    locale_titles: dict[str, str]
    alt_en_title: str


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611349565788,
        "label": "Autoportret slomkowy Amsterdam F365v",
        "old_pl_titles": ("Autoportret w słomkowym kapeluszu",),
        "new_pl_title": (
            "Autoportret w słomkowym kapeluszu (z Amsterdamu) "
            "(lub Autoportret w słomkowym kapeluszu i pasiastym garniturze)"
        ),
        "original_title": (
            "Zelfportret met strohoed (Amsterdam) "
            "(of Zelfportret met strohoed en gestreept pak)"
        ),
        "english_title": (
            "Self-Portrait with a Straw Hat (Amsterdam) "
            "(or Self-Portrait with a Straw Hat in a Striped Suit)"
        ),
        "locale_titles": {
            "en": (
                "Self-Portrait with a Straw Hat (Amsterdam) "
                "(or Self-Portrait with a Straw Hat in a Striped Suit)"
            ),
            "de": (
                "Selbstbildnis mit Strohhut (Amsterdam) "
                "(oder Selbstbildnis mit Strohhut im gestreiften Anzug)"
            ),
            "fr": (
                "Autoportrait au chapeau de paille (Amsterdam) "
                "(ou Autoportrait au chapeau de paille et costume rayé)"
            ),
            "es": (
                "Autorretrato con sombrero de paja (Amsterdam) "
                "(o Autorretrato con sombrero de paja y traje a rayas)"
            ),
            "nl": (
                "Zelfportret met strohoed (Amsterdam) "
                "(of Zelfportret met strohoed en gestreept pak)"
            ),
            "it": (
                "Autoritratto con cappello di paglia (Amsterdam) "
                "(o Autoritratto con cappello di paglia e abito gessato)"
            ),
        },
        "alt_en_title": "Self-Portrait with a Straw Hat (Amsterdam)",
    },
    {
        "product_id": 15611349827932,
        "label": "Autoportret slomkowy Detroit F526",
        "old_pl_titles": ("Autoportret w słomkowym kapeluszu",),
        "new_pl_title": (
            "Autoportret w słomkowym kapeluszu (z Detroit) "
            "(lub Autoportret w słomkowym kapeluszu (w niebieskiej bluzie))"
        ),
        "original_title": (
            "Zelfportret met strohoed (Detroit) "
            "(of Zelfportret met strohoed (met blauwe kiel))"
        ),
        "english_title": (
            "Self-Portrait with a Straw Hat (Detroit) "
            "(or Self-Portrait with a Straw Hat (in a Blue Smock))"
        ),
        "locale_titles": {
            "en": (
                "Self-Portrait with a Straw Hat (Detroit) "
                "(or Self-Portrait with a Straw Hat (in a Blue Smock))"
            ),
            "de": (
                "Selbstbildnis mit Strohhut (Detroit) "
                "(oder Selbstbildnis mit Strohhut (im blauen Kittel))"
            ),
            "fr": (
                "Autoportrait au chapeau de paille (Detroit) "
                "(ou Autoportrait au chapeau de paille (en blouse bleue))"
            ),
            "es": (
                "Autorretrato con sombrero de paja (Detroit) "
                "(o Autorretrato con sombrero de paja (con blusa azul))"
            ),
            "nl": (
                "Zelfportret met strohoed (Detroit) "
                "(of Zelfportret met strohoed (met blauwe kiel))"
            ),
            "it": (
                "Autoritratto con cappello di paglia (Detroit) "
                "(o Autoritratto con cappello di paglia (con camice blu))"
            ),
        },
        "alt_en_title": "Self-Portrait with a Straw Hat (Detroit)",
    },
    {
        "product_id": 15611350647132,
        "label": "Autoportret filcowy",
        "old_pl_titles": (
            "Autoportret w szarym filcowym kapeluszu",
            "Autoportret w filcowym kapeluszu",
        ),
        "new_pl_title": (
            "Autoportret w filcowym kapeluszu "
            "(lub Autoportret w szarym filcowym kapeluszu (z Amsterdamu))"
        ),
        "original_title": (
            "Zelfportret met vilthoed (of Zelfportret met grijze vilthoed (Amsterdam))"
        ),
        "english_title": (
            "Self-Portrait with a Felt Hat "
            "(or Self-Portrait with Grey Felt Hat (Amsterdam))"
        ),
        "locale_titles": {
            "en": (
                "Self-Portrait with a Felt Hat "
                "(or Self-Portrait with Grey Felt Hat (Amsterdam))"
            ),
            "de": (
                "Selbstbildnis mit Filzhut "
                "(oder Selbstbildnis mit grauem Filzhut (Amsterdam))"
            ),
            "fr": (
                "Autoportrait au chapeau de feutre "
                "(ou Autoportrait au chapeau de feutre gris (Amsterdam))"
            ),
            "es": (
                "Autorretrato con sombrero de fieltro "
                "(o Autorretrato con sombrero de fieltro gris (Amsterdam))"
            ),
            "nl": (
                "Zelfportret met vilthoed "
                "(of Zelfportret met grijze vilthoed (Amsterdam))"
            ),
            "it": (
                "Autoritratto con cappello di feltro "
                "(o Autoritratto con cappello di feltro grigio (Amsterdam))"
            ),
        },
        "alt_en_title": "Self-Portrait with Grey Felt Hat",
    },
    {
        "product_id": 15611349270876,
        "label": "Autoportret jako malarz",
        "old_pl_titles": ("Autoportret jako malarz",),
        "new_pl_title": "Autoportret przed sztalugą (lub Autoportret jako malarz)",
        "original_title": "Zelfportret als schilder (of Zelfportret voor de ezels)",
        "english_title": (
            "Self-Portrait as a Painter (or Self-Portrait in Front of the Easel)"
        ),
        "locale_titles": {
            "en": (
                "Self-Portrait as a Painter (or Self-Portrait in Front of the Easel)"
            ),
            "de": (
                "Selbstbildnis als Maler (oder Selbstbildnis vor der Staffelei)"
            ),
            "fr": (
                "Autoportrait en tant que peintre "
                "(ou Autoportrait devant le chevalet)"
            ),
            "es": (
                "Autorretrato como pintor (o Autorretrato ante el caballete)"
            ),
            "nl": "Zelfportret als schilder (of Zelfportret voor de ezels)",
            "it": (
                "Autoritratto come pittore (o Autoritratto davanti al cavalletto)"
            ),
        },
        "alt_en_title": "Self-Portrait as a Painter",
    },
    {
        "product_id": 15611348910428,
        "label": "Autoportret 1887",
        "old_pl_titles": ("Autoportret 1887",),
        "new_pl_title": (
            "Autoportret (z Wiednia) (lub Autoportret w ciemnym kapeluszu i marynarce)"
        ),
        "original_title": (
            "Zelfportret (Wien) (of Portret van Vincent van Gogh door hemzelf)"
        ),
        "english_title": "Self-Portrait (Vienna) (or Self-Portrait)",
        "locale_titles": {
            "en": "Self-Portrait (Vienna) (or Self-Portrait)",
            "de": "Selbstbildnis (Wien) (oder Selbstporträt (Wien))",
            "fr": "Autoportrait (Vienne)",
            "es": "Autorretrato (Viena)",
            "nl": "Zelfportret (Wien) (of Portret van Vincent van Gogh door hemzelf)",
            "it": "Autoritratto (Vienna)",
        },
        "alt_en_title": "Self-Portrait (Vienna)",
    },
    {
        "product_id": 15611348386140,
        "label": "Autoportret Orsay",
        "old_pl_titles": ("Autoportret",),
        "new_pl_title": (
            "Autoportret (z Musée d'Orsay) (lub Autoportret na jasnoniebieskim tle)"
        ),
        "original_title": (
            "Zelfportret (Musée d'Orsay) (of Zelfportret met wervelende achtergrond)"
        ),
        "english_title": (
            "Self-Portrait (Musée d'Orsay) (or Self-Portrait with Swirling Background)"
        ),
        "locale_titles": {
            "en": (
                "Self-Portrait (Musée d'Orsay) "
                "(or Self-Portrait with Swirling Background)"
            ),
            "de": (
                "Selbstbildnis (Musée d'Orsay) "
                "(oder Selbstbildnis vor wirbelndem Hintergrund)"
            ),
            "fr": (
                "Autoportrait (Musée d'Orsay) "
                "(ou Portrait de l'artiste par lui-même)"
            ),
            "es": (
                "Autorretrato (Musée d'Orsay) (o Autorretrato con fondo torbellino)"
            ),
            "nl": (
                "Zelfportret (Musée d'Orsay) "
                "(of Zelfportret met wervelende achtergrond)"
            ),
            "it": (
                "Autoritratto (Musée d'Orsay) (o Autoritratto con sfondo a volute)"
            ),
        },
        "alt_en_title": "Self-Portrait (Musée d'Orsay)",
    },
    {
        "product_id": 15611333116252,
        "label": "Aleja topoli jesienia",
        "old_pl_titles": ("Aleja topoli jesienią",),
        "new_pl_title": "Aleja topoli jesienią (lub Aleja topoli o zmierzchu)",
        "original_title": "Populierenlaan in de herfst (of Laan met populieren in de herfst)",
        "english_title": "Avenue of Poplars in Autumn (or Avenue of Poplars at Sunset)",
        "locale_titles": {
            "en": "Avenue of Poplars in Autumn (or Avenue of Poplars at Sunset)",
            "de": "Pappelallee im Herbst (oder Allee mit Pappeln im Herbst)",
            "fr": (
                "Allée de peupliers en automne "
                "(ou L'allée des peupliers en automne)"
            ),
            "es": "Avenida de álamos en otoño (o Paseo de álamos en otoño)",
            "nl": "Populierenlaan in de herfst (of Laan met populieren in de herfst)",
            "it": "Viale di pioppi in autunno (o Viale con pioppi in autunno)",
        },
        "alt_en_title": "Avenue of Poplars in Autumn",
    },
)


def _set_detail_value(body_html: str, label: str, value: str) -> str:
    pat = re.compile(
        r"(<strong>\s*" + re.escape(label) + r"\s*:\s*</strong>\s*)([^<]*)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError(f"Brak pola «{label}» w body_html.")
    return pat.sub(lambda m: m.group(1) + escape(value, quote=False), body_html, count=1)


def _set_display_title(body_html: str, title: str) -> str:
    pat = re.compile(
        r"(font-size:\s*20px[^>]*>)([^<]+)(</div>)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError("Brak naglowka tytulu w body_html.")
    return pat.sub(
        lambda m: m.group(1) + escape(title, quote=False) + m.group(3),
        body_html,
        count=1,
    )


def _replace_titles(body_html: str, old_titles: tuple[str, ...], new_title: str) -> str:
    out = body_html
    for old in old_titles:
        if old in out and old not in new_title:
            out = out.replace(old, new_title)
    return out


def _apply_locale_titles(
    body_html: str,
    loc: str,
    *,
    original_title: str,
    locale_titles: dict[str, str],
) -> str:
    title = locale_titles.get(loc, "")
    if not title:
        return body_html
    labels = BODY_LABELS_I18N[loc]
    updated = body_html
    updated = _set_detail_value(updated, labels["tytul_orig"], original_title)
    updated = _set_detail_value(updated, labels["tytul"], title)
    updated = _set_display_title(updated, title)
    return updated


def _apply_product(shop: str, token: str, cfg: ProductTitles) -> None:
    pid = cfg["product_id"]
    gid = sc.product_gid(pid)
    print(f"\n=== {cfg['label']} (id={pid}) ===")

    prod = sc.get_product(shop, token, pid)
    if not prod.get("id"):
        raise RuntimeError(f"Brak produktu id={pid}")

    pl_body = prod.get("body_html") or ""
    pl_body = _replace_titles(pl_body, cfg["old_pl_titles"], cfg["new_pl_title"])
    pl_body = _set_display_title(pl_body, cfg["new_pl_title"])
    pl_body = _set_detail_value(
        pl_body, BODY_LABELS_I18N["pl"]["tytul"], cfg["new_pl_title"],
    )
    pl_body = _set_detail_value(
        pl_body, BODY_LABELS_I18N["pl"]["tytul_orig"], cfg["original_title"],
    )

    new_product_title = f"{ARTIST} - {cfg['new_pl_title']}"
    title_tag, meta_desc, handle = build_seo(
        tytul=cfg["new_pl_title"],
        artysta=ARTIST,
        gatunek="",
        nurt="",
    )
    print(f"  tytul: {new_product_title}")

    sc.update_product(
        shop,
        token,
        pid,
        {"title": new_product_title, "handle": handle, "body_html": pl_body},
    )
    sc.set_seo_metafields(shop, token, pid, title_tag=title_tag, description_tag=meta_desc)

    for loc in SUPPORTED_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = tr.get("body_html") or ""
        if not body:
            continue
        updated = _apply_locale_titles(
            body,
            loc,
            original_title=cfg["original_title"],
            locale_titles=cfg["locale_titles"],
        )
        sc.register_translations(
            shop, token, resource_gid=gid, locale=loc, fields={"body_html": updated},
        )

    alt_en = cfg["alt_en_title"]
    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(ARTIST, alt_en)
        elif "(preview)" in src:
            alt = preview_alt_text(ARTIST, alt_en)
        elif "(mockup)" in src:
            alt = f"{ARTIST} - {alt_en} - (mockup)"
        else:
            alt = f"{ARTIST} - {alt_en}"
        sc.rest_put(
            shop,
            token,
            f"products/{pid}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )

    pl2 = sc.get_product(shop, token, pid).get("body_html") or ""
    print(f"  PL: {extract_display_title_from_body_html(pl2)}")


def main() -> int:
    shop, token = sc.load_session()
    for cfg in PRODUCTS:
        _apply_product(shop, token, cfg)
    print("\nGotowe — 7 produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
