"""Szablon HTML dla body_html produktu (opis obrazu: 3-4 akapity).

Sekcja prawej kolumny ('SZCZEGOLY') jest LOKALIZOWANA - etykiety i naglowek
dostarcza caller (np. z `body_i18n.body_labels(lang)`). Domyslne wartosci sa po
polsku (kompatybilnosc wsteczna z poprzednim API funkcji).
"""
from __future__ import annotations

import re
from html import escape, unescape

from .body_i18n import body_labels

_TEMPLATE = """<table style="width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.7;">
<tbody>
<tr>
<td colspan="3" style="padding-bottom: 16px;">
<div style="font-size: 20px; font-weight: bold; margin-bottom: 6px;">{tytul_obrazu}</div>
<div style="font-size: 13px; font-weight: bold; color: #888; margin-bottom: 0px;">{artysta}</div>
<div style="font-size: 13px; color: #888; margin-bottom: 16px;">{data}</div>
<div style="border-top: 1px solid rgba(255,255,255,0.2); width: 100%;"><br></div>
</td>
</tr>
<tr>
<td style="width: 55%; vertical-align: top; padding-top: 16px; padding-right: 32px;">{akapity_html}<br>
</td>
<td style="width: 1px; padding-top: 16px; padding-right: 32px;">
<div style="width: 1px; background: rgba(255,255,255,0.2); height: 100%; min-height: 120px;"><br></div>
</td>
<td style="width: 45%; vertical-align: top; padding-top: 16px;">
<strong>{header}</strong><br><br><strong>{lbl_tytul}: </strong>{tytul_obrazu}<br><strong>{lbl_tytul_orig}: </strong> {tytul_orginalny}<br><strong>{lbl_autor}: </strong>{artysta}<br><strong>{lbl_data}: </strong> {data_powstania}<br><strong>{lbl_miejsce}: </strong>{miejsce_powstania}<br><strong>{lbl_typ} :</strong> {val_typ}<br><strong>{lbl_technika}: </strong>{technika}<br><strong>{lbl_gatunek}: </strong>{gatunek}<br><strong>{lbl_nurt}: </strong>{nurt}<br><strong>{lbl_forma}: </strong>{forma}</td>
</tr>
</tbody>
</table>"""


_ARTIST_BODY_TEMPLATE = """<div style="max-width: 900px; margin-bottom: 40px;">
  <h4>{lifespan}</h4>
  <div style="height: 24px;"></div>
  <div style="display: flex; gap: 48px; align-items: flex-start; flex-wrap: wrap;">
{portrait_html}
    <div style="flex: 1; min-width: 260px;">
{paragraphs_html}
    </div>
  </div>
</div>"""

_ARTIST_PORTRAIT_TEMPLATE = (
    '    <img src="{src}" alt="{alt}" style="width: 220px; height: auto; '
    "flex-shrink: 0; border-radius: 50%; border: 3px solid rgba(180,150,100,0.6); "
    'box-shadow: 0 0 40px rgba(0,0,0,0.8); filter: grayscale(60%);">'
)


def build_artist_collection_body_html(
    *,
    title: str,
    description: str,
    lifespan: str = "",
    portrait_url: str = "",
) -> str:
    """Buduje body_html strony kolekcji artysty (jak u pozostalych artystow).

    Uklad: <h4>daty zycia</h4> + okragly portret + akapity krotkiego opisu.

    Args:
        title: tytul kolekcji 'Nazwisko, Imie' (uzywany jako alt portretu).
        description: krotki opis — akapity rozdzielone pustymi liniami (lub \\n).
        lifespan: daty zycia, np. '14 Lis 1840 - 5 Gru 1926' (moze byc puste).
        portrait_url: CDN URL portretu artysty (moze byc puste — wtedy bez zdjecia).
    """
    def e(s: str) -> str:
        return escape(s or "", quote=False)

    # Akapity: rozdzielone pusta linia; fallback: pojedyncze \n.
    raw = (description or "").strip()
    chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
    if not chunks and raw:
        chunks = [c.strip() for c in raw.split("\n") if c.strip()]
    paras: list[str] = []
    for i, chunk in enumerate(chunks):
        margin = "0 0 18px 0" if i < len(chunks) - 1 else "0"
        paras.append(
            f'      <p style="font-size: 15px; line-height: 1.85; margin: {margin}; '
            f'opacity: 0.85;">{e(chunk)}</p>'
        )
    paragraphs_html = "\n".join(paras)

    portrait_html = ""
    if portrait_url:
        portrait_html = _ARTIST_PORTRAIT_TEMPLATE.format(
            src=escape(portrait_url, quote=True), alt=escape(title, quote=True)
        )

    return _ARTIST_BODY_TEMPLATE.format(
        lifespan=e(lifespan) or "&nbsp;",
        portrait_html=portrait_html,
        paragraphs_html=paragraphs_html,
    )


_DESC_COLUMN_RE = re.compile(
    r'<td[^>]*width:\s*55%[^>]*>(.*?)</td>',
    re.DOTALL | re.IGNORECASE,
)


def extract_paragraphs_from_body_html(body_html: str) -> list[str]:
    """Wyciaga akapity opisu z lewej kolumny szablonu produktu (separator `<br><br>`)."""
    if not (body_html or "").strip():
        return []
    m = _DESC_COLUMN_RE.search(body_html)
    if not m:
        return []
    raw = m.group(1)
    raw = re.sub(r"<br\s*/?>\s*$", "", raw.strip(), flags=re.I)
    parts = re.split(r"<br\s*/?>\s*<br\s*/?>", raw, flags=re.I)
    out: list[str] = []
    for part in parts:
        text = re.sub(r"<[^>]+>", "", part)
        text = unescape(text).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            out.append(text)
    return out[:4]


_DISPLAY_TITLE_RE = re.compile(
    r'font-size:\s*20px[^>]*>([^<]+)</div>',
    re.IGNORECASE,
)
_UNKNOWN_TITLES = frozenset({"nieznana", "unknown", "n/a", "—", "-"})


def _detail_value(body_html: str, label: str) -> str:
    if not (label or "").strip():
        return ""
    pat = re.compile(
        r"<strong>\s*" + re.escape(label.strip()) + r"\s*:\s*</strong>\s*([^<]*)",
        re.IGNORECASE,
    )
    m = pat.search(body_html or "")
    if not m:
        return ""
    text = unescape(m.group(1)).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_display_title_from_body_html(body_html: str) -> str:
    """Tytul obrazu z naglowka szablonu produktu (kolumna PL lub tlumaczenie)."""
    m = _DISPLAY_TITLE_RE.search(body_html or "")
    if not m:
        return ""
    text = unescape(m.group(1)).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_original_title_from_body_html(body_html: str) -> str:
    """Tytul oryginalny z kolumny SZCZEGOLY (etykieta we wszystkich locale)."""
    from .body_i18n import BODY_LABELS_I18N

    for labels in BODY_LABELS_I18N.values():
        lbl = (labels.get("tytul_orig") or "").strip()
        if not lbl:
            continue
        val = _detail_value(body_html, lbl)
        if val and val.lower() not in _UNKNOWN_TITLES:
            return val
    return ""


_HEADER_LIFESPAN_RE = re.compile(
    r"font-size:\s*20px[^>]*>[^<]+</div>\s*"
    r'<div style="font-size:\s*13px;\s*font-weight:\s*bold[^>]*>[^<]+</div>\s*'
    r'<div style="font-size:\s*13px;\s*color:\s*#888[^>]*>([^<]*)</div>',
    re.IGNORECASE,
)


def extract_product_body_facts(body_html: str, lang: str = "pl") -> dict[str, str]:
    """Wartosci pol SZCZEGOLY + lifespan z naglowka (do budowy tlumaczen body_html)."""
    lab = body_labels(lang)
    fact_keys = (
        "tytul",
        "tytul_orig",
        "autor",
        "data_powstania",
        "miejsce_powstania",
        "technika",
        "gatunek",
        "nurt",
        "forma",
    )
    out: dict[str, str] = {}
    for key in fact_keys:
        lbl = (lab.get(key) or "").strip()
        out[key] = _detail_value(body_html, lbl) if lbl else ""
    m = _HEADER_LIFESPAN_RE.search(body_html or "")
    out["lifespan"] = unescape(m.group(1)).strip() if m else ""
    return out


def build_locale_body_html_from_pl(
    pl_body: str,
    loc: str,
    *,
    locale_title: str,
    original_title: str,
    artist: str,
) -> str:
    """Buduje body_html tlumaczenia z szablonu PL (gdy brak istniejacego tlumaczenia)."""
    from .body_i18n import translate_field_value_or_pl

    facts = extract_product_body_facts(pl_body, "pl")
    akapity = extract_paragraphs_from_body_html(pl_body)

    def _tr(pl_value: str) -> str:
        return translate_field_value_or_pl((pl_value or "").strip(), loc)

    return build_body_html(
        tytul_obrazu=locale_title,
        artysta=(artist or facts.get("autor") or "").strip(),
        data=facts.get("lifespan") or "",
        akapity=akapity,
        tytul_orginalny=original_title,
        data_powstania=_tr(facts.get("data_powstania") or ""),
        miejsce_powstania=_tr(facts.get("miejsce_powstania") or ""),
        technika=_tr(facts.get("technika") or ""),
        gatunek=_tr(facts.get("gatunek") or ""),
        nurt=_tr(facts.get("nurt") or ""),
        forma=_tr(facts.get("forma") or ""),
        lang=loc,
    )


def set_detail_value_in_body_html(body_html: str, label: str, value: str) -> str:
    """Podmienia wartosc pola SZCZEGOLY (etykieta + strong) w body_html."""
    pat = re.compile(
        r"(<strong>\s*" + re.escape(label) + r"\s*:\s*</strong>\s*)([^<]*)",
        re.IGNORECASE,
    )
    if not pat.search(body_html or ""):
        raise ValueError(f"Brak pola «{label}» w body_html.")
    return pat.sub(
        lambda m: m.group(1) + escape(value, quote=False),
        body_html,
        count=1,
    )


def set_display_title_in_body_html(body_html: str, title: str) -> str:
    """Podmienia naglowek tytulu obrazu (font-size: 20px) w body_html."""
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


def replace_paragraphs_in_body_html(body_html: str, akapity: list[str]) -> str:
    """Podmienia tylko akapity w lewej kolumnie — reszta szablonu bez zmian."""
    if not (body_html or "").strip():
        raise ValueError("Pusty body_html — brak szablonu do aktualizacji.")
    m = _DESC_COLUMN_RE.search(body_html)
    if not m:
        raise ValueError("Nierozpoznany format body_html (brak kolumny 55%).")

    def e(s: str) -> str:
        return escape(s or "", quote=False)

    shown = [a for a in akapity if isinstance(a, str) and a.strip()][:4]
    akapity_html = "<br><br>".join(e(a) for a in shown)
    new_inner = f"{akapity_html}<br>\n"
    start, end = m.span(1)
    return body_html[:start] + new_inner + body_html[end:]


def build_body_html(
    *,
    tytul_obrazu: str,
    artysta: str,
    data: str,
    akapity: list[str],
    tytul_orginalny: str,
    data_powstania: str,
    miejsce_powstania: str,
    technika: str,
    gatunek: str,
    nurt: str,
    forma: str,
    lang: str = "pl",
    labels: dict[str, str] | None = None,
) -> str:
    """Buduje body_html dla produktu.

    Args:
        lang: locale dla etykiet/naglowka, np. 'pl' / 'en' / 'de' / 'fr' / 'es' /
              'nl' / 'it'. Uzywane do pobrania domyslnych etykiet z
              `body_i18n.body_labels(lang)`.
        labels: opcjonalne nadpisanie pojedynczych etykiet (klucze: 'header',
                'tytul', 'tytul_orig', 'autor', 'data_powstania',
                'miejsce_powstania', 'typ', 'typ_value', 'technika', 'gatunek',
                'nurt', 'forma'). Jesli podane - nadpisuje wartosci z `lang`.

    Wszystkie pozostale argumenty sa wartosciami danego pola (string).
    """
    def e(s: str) -> str:
        return escape(s or "", quote=False)

    shown = [a for a in akapity if isinstance(a, str) and a.strip()][:4]
    akapity_html = "<br><br>".join(e(a) for a in shown)
    lab = dict(body_labels(lang))
    if labels:
        lab.update({k: v for k, v in labels.items() if v})

    return _TEMPLATE.format(
        tytul_obrazu=e(tytul_obrazu),
        artysta=e(artysta),
        data=e(data) or "&nbsp;",
        akapity_html=akapity_html,
        tytul_orginalny=e(tytul_orginalny),
        data_powstania=e(data_powstania),
        miejsce_powstania=e(miejsce_powstania),
        technika=e(technika),
        gatunek=e(gatunek),
        nurt=e(nurt),
        forma=e(forma),
        header=e(lab.get("header") or ""),
        lbl_tytul=e(lab.get("tytul") or ""),
        lbl_tytul_orig=e(lab.get("tytul_orig") or ""),
        lbl_autor=e(lab.get("autor") or ""),
        lbl_data=e(lab.get("data_powstania") or ""),
        lbl_miejsce=e(lab.get("miejsce_powstania") or ""),
        lbl_typ=e(lab.get("typ") or ""),
        val_typ=e(lab.get("typ_value") or ""),
        lbl_technika=e(lab.get("technika") or ""),
        lbl_gatunek=e(lab.get("gatunek") or ""),
        lbl_nurt=e(lab.get("nurt") or ""),
        lbl_forma=e(lab.get("forma") or ""),
    )
