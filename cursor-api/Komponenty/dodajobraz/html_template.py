"""Szablon HTML dla body_html produktu (opis obrazu).

Sekcja prawej kolumny ('SZCZEGOLY') jest LOKALIZOWANA - etykiety i naglowek
dostarcza caller (np. z `body_i18n.body_labels(lang)`). Domyslne wartosci sa po
polsku (kompatybilnosc wsteczna z poprzednim API funkcji).
"""
from __future__ import annotations

from html import escape

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
<td style="width: 55%; vertical-align: top; padding-top: 16px; padding-right: 32px;">{akapit1}<br><br>{akapit2}<br><br>{akapit3}<br>
</td>
<td style="width: 1px; padding-top: 16px; padding-right: 32px;">
<div style="width: 1px; background: rgba(255,255,255,0.2); height: 100%; min-height: 120px;"><br></div>
</td>
<td style="width: 45%; vertical-align: top; padding-top: 16px;">
<strong>{header}</strong><br><br><strong>{lbl_tytul}: </strong>{tytul_obrazu}<br><strong>{lbl_tytul_orig}: </strong> {tytul_orginalny}<br><strong>{lbl_autor}: </strong>{artysta}<br><strong>{lbl_data}: </strong> {data_powstania}<br><strong>{lbl_miejsce}: </strong>{miejsce_powstania}<br><strong>{lbl_typ} :</strong> {val_typ}<br><strong>{lbl_technika}: </strong>{technika}<br><strong>{lbl_gatunek}: </strong>{gatunek}<br><strong>{lbl_nurt}: </strong>{nurt}<br><strong>{lbl_forma}: </strong>{forma}</td>
</tr>
</tbody>
</table>"""


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

    a1, a2, a3 = [e(a) for a in akapity]
    lab = dict(body_labels(lang))
    if labels:
        lab.update({k: v for k, v in labels.items() if v})

    return _TEMPLATE.format(
        tytul_obrazu=e(tytul_obrazu),
        artysta=e(artysta),
        data=e(data) or "&nbsp;",
        akapit1=a1,
        akapit2=a2,
        akapit3=a3,
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
