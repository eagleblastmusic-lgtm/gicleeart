"""Wariant ramki jak w Shopify: drewno / rozmiar / kolor (option1 / option2 / option3)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Fallback gdy brak szablonu lokalnego (zgodnie ze sklepem Giclee)
_FALLBACK_DREWNO = ("Dąb", "Sosna")
_FALLBACK_ROZMIAR = ("M", "L", "XL")
_FALLBACK_KOLOR = ("Czarny", "Jasny Brąz", "Brąz", "Ciemny Brąz")


@dataclass(frozen=True)
class FrameFieldOptions:
    """Wartosci i etykiety pol ramki — z domyslnego szablonu wariantow (jak w Shopify)."""

    drewno_values: tuple[str, ...]
    rozmiar_values: tuple[str, ...]
    kolor_values: tuple[str, ...]
    label_drewno: str
    label_rozmiar: str
    label_kolor: str


def _classify_option_field(name: str) -> str | None:
    """Mapuje nazwe opcji produktu Shopify na pole ramka_*."""
    n = (name or "").strip().lower()
    if not n:
        return None
    if "kolor" in n:
        return "ramka_kolor"
    if "rozmiar" in n or "wymiar" in n:
        return "ramka_rozmiar"
    if "drewn" in n or "sosn" in n or "dąb" in n or n == "dab":
        return "ramka_drewno"
    return None


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        s = str(x).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def frame_field_options_from_template(template: Any | None) -> FrameFieldOptions:
    """Buduje listy wartosci z opcji szablonu (sortowanie po `position`).

    Nazwy opcji (Kolor / Rozmiar / Rodzaj drewna) mapujemy na pola semantyczne.
    Gdy nazwa nie pasuje — kolejnosc pozycji 1→drewno, 2→rozmiar, 3→kolor (rzadki przypadek).
    """
    fd = list(_FALLBACK_DREWNO)
    fr = list(_FALLBACK_ROZMIAR)
    fk = list(_FALLBACK_KOLOR)
    ld, lr, lk = "Drewno (jak w sklepie)", "Rozmiar", "Kolor ramki"

    buckets: dict[str, list[str]] = {
        "ramka_drewno": [],
        "ramka_rozmiar": [],
        "ramka_kolor": [],
    }
    labels: dict[str, str] = {}

    opts_raw = list((template.options if template else []) or [])
    opts_sorted = sorted(
        opts_raw,
        key=lambda o: int((o or {}).get("position") or 0),
    )

    pos_fallback: list[tuple[str, list[str], str]] = []
    for opt in opts_sorted:
        if not isinstance(opt, dict):
            continue
        nm = str(opt.get("name") or "").strip()
        vals = [str(v).strip() for v in (opt.get("values") or []) if str(v).strip()]
        field = _classify_option_field(nm)
        if field:
            buckets[field] = _dedupe_preserve(vals)
            labels[field] = nm
        else:
            pos_fallback.append((nm, _dedupe_preserve(vals), nm))

    for i, (_nm, vals, title) in enumerate(pos_fallback):
        key = ("ramka_drewno", "ramka_rozmiar", "ramka_kolor")[min(i, 2)]
        if not buckets[key]:
            buckets[key] = vals
            labels[key] = title

    if buckets["ramka_drewno"]:
        fd = buckets["ramka_drewno"]
        ld = labels.get("ramka_drewno", ld)
    if buckets["ramka_rozmiar"]:
        fr = buckets["ramka_rozmiar"]
        lr = labels.get("ramka_rozmiar", lr)
    if buckets["ramka_kolor"]:
        fk = buckets["ramka_kolor"]
        lk = labels.get("ramka_kolor", lk)

    return FrameFieldOptions(
        drewno_values=tuple(fd),
        rozmiar_values=tuple(fr),
        kolor_values=tuple(fk),
        label_drewno=ld,
        label_rozmiar=lr,
        label_kolor=lk,
    )


def load_frame_field_options() -> FrameFieldOptions:
    """Domyslny szablon z `dodajobraz` / `variant_templates.json`."""
    try:
        from Komponenty.dodajobraz.templates import get_default

        t = get_default()
    except Exception:  # noqa: BLE001
        t = None
    return frame_field_options_from_template(t)


def combobox_values_with_current(allowed: tuple[str, ...], current: str) -> tuple[str, ...]:
    """Zapewnia, ze biezaca wartosc zamowienia jest na liscie (stare / reczne wpisy)."""
    cur = (current or "").strip()
    if not cur:
        return allowed
    if cur in allowed:
        return allowed
    return (cur,) + allowed

# Stara heurystyka jednym tagiem (np. zamowienia sprzed podzialu pol)
_LEGACY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bd[aą]b\b.*\bxl\b", re.IGNORECASE), "Dab XL"),
    (re.compile(r"\bd[aą]b\b.*\bl\b", re.IGNORECASE), "Dab L"),
    (re.compile(r"\bd[aą]b\b.*\bm\b", re.IGNORECASE), "Dab M"),
    (re.compile(r"\bd[aą]b\b.*\bs\b", re.IGNORECASE), "Dab M"),
    (re.compile(r"\bsosn[aę]\b.*\bxl\b", re.IGNORECASE), "Sosna XL"),
    (re.compile(r"\bsosn[aę]\b.*\bl\b", re.IGNORECASE), "Sosna L"),
    (re.compile(r"\bsosn[aę]\b.*\bm\b", re.IGNORECASE), "Sosna M"),
    (re.compile(r"\bsosn[aę]\b.*\bs\b", re.IGNORECASE), "Sosna M"),
]


def legacy_compact_label(variant_title: str, *, fallback: str = "Dab M") -> str:
    """Jedna krotka etykieta (stary format produkcji)."""
    v = (variant_title or "").strip()
    if not v:
        return fallback
    for pattern, label in _LEGACY_PATTERNS:
        if pattern.search(v):
            return label
    return fallback


def _size_code_from_label(rozmiar: str) -> str:
    """Mapuje etykiete rozmiaru ze sklepu (np. 50x70) na M / L / XL dla szablonu wymiarow."""
    r = (rozmiar or "").upper().replace(" ", "")
    if not r:
        return "M"
    if "XL" in r and "XXL" not in r:
        return "XL"
    m = re.search(r"(\d+)\s*[xX×]\s*(\d+)", r)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        longest = max(w, h)
        if longest >= 100:
            return "XL"
        if longest >= 70:
            return "L"
        return "M"
    if "L" in r and "XL" not in r:
        return "L"
    if r in ("S", "M"):
        return "M"
    return "M"


def shipping_lookup_key(order: dict[str, Any]) -> str:
    """Klucz do tabeli wymiarow paczki (np. 'DAB M') — ze sklepowych pol lub legacy."""
    migrate_order_frame_fields(order)
    d_raw = str(order.get("ramka_drewno") or "").strip()
    r_raw = str(order.get("ramka_rozmiar") or "").strip()
    drewno_u = d_raw.upper()
    if "SOSNA" in drewno_u or "SOSN" in drewno_u:
        wood = "SOSNA"
    else:
        wood = "DAB"
    code = _size_code_from_label(r_raw)
    return f"{wood} {code}"


def parse_shopify_variant_title(variant_title: str) -> tuple[str, str, str]:
    """Parsuje `variant_title` z zamowienia Shopify — tak jak w koszyku: opcje przez ' / '."""
    v = (variant_title or "").strip()
    if not v:
        return ("", "", "")
    if " / " in v:
        parts = [p.strip() for p in v.split(" / ")]
        while len(parts) < 3:
            parts.append("")
        return (parts[0], parts[1], parts[2][:240])
    # Jedna krotka nazwa drewna (np. szablon reczny) — bez mylenia z 'Dab M'
    norm = v.casefold().replace("ą", "a")
    if norm in ("dab", "dąb", "sosna"):
        return (v, "", "")
    lab = legacy_compact_label(v)
    tok = lab.split()
    if len(tok) >= 2:
        return (tok[0], tok[-1], "")
    return (lab, "", "")


def combined_label(drewno: str, rozmiar: str, kolor: str) -> str:
    """Laczona etykieta do `ramka_wariant` (wyszukiwanie, CSV, kompatybilnosc)."""
    parts = [p.strip() for p in (drewno, rozmiar, kolor) if p and str(p).strip()]
    return " / ".join(parts)


def sync_combined_from_parts(o: dict[str, Any]) -> None:
    """Uaktualnia `ramka_wariant` z pol skladowych."""
    o["ramka_wariant"] = combined_label(
        str(o.get("ramka_drewno") or ""),
        str(o.get("ramka_rozmiar") or ""),
        str(o.get("ramka_kolor") or ""),
    )


def migrate_order_frame_fields(o: dict[str, Any]) -> None:
    """Uzupelnia ramka_drewno / ramka_rozmiar / ramka_kolor przy starych wpisach."""
    d = str(o.get("ramka_drewno") or "").strip()
    r = str(o.get("ramka_rozmiar") or "").strip()
    k = str(o.get("ramka_kolor") or "").strip()
    if d or r or k:
        sync_combined_from_parts(o)
        return
    rw = str(o.get("ramka_wariant") or "").strip()
    if not rw:
        o["ramka_drewno"] = "Dąb"
        o["ramka_rozmiar"] = ""
        o["ramka_kolor"] = ""
        sync_combined_from_parts(o)
        return
    if " / " in rw:
        dd, rr, kk = parse_shopify_variant_title(rw)
    else:
        dd, rr, kk = parse_shopify_variant_title(rw)
    o["ramka_drewno"] = dd or "Dąb"
    o["ramka_rozmiar"] = rr
    o["ramka_kolor"] = kk
    sync_combined_from_parts(o)


# Alias pod testy / stary kod
_detect_frame_variant = legacy_compact_label
