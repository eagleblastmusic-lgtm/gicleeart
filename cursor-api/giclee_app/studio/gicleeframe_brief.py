"""GICLÉE FRAME™ — statyczny design brief (planning layer). Pure, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass

COMPONENT_NAME = "GICLÉE FRAME™"
COMPONENT_ROLE = "Premium komponent strony"
COMPONENT_DESCRIPTION = (
    "Subtelny znak technologii ramy — podpis systemu, premium label, section label "
    "lub hero label dla strony Giclée Art. Museum-quality, editorial, bez taniego badge'a."
)

STATUS_STRIP = (
    "Status: planowanie lokalne · Shopify: zablokowane · "
    "Sync/deploy: zablokowane · Writer/save: zablokowane"
)

PLANNING_BADGE = "local planning only"
DRY_RUN_BADGE = "dry-run · nic nie zapisano"
NEXT_PHASE_NOTE = "Gotowe do kolejnej fazy: po akceptacji"

WORKFLOW_SUMMARY = (
    "GICLÉE FRAME™ — premium brand/design component. "
    "Panel planistyczny w Studio: warianty, zasady wizualne i motion, readiness, "
    "podgląd przyszłego outputu motywu. Bez zapisu, bez Shopify."
)


@dataclass(frozen=True)
class GicleeFrameVariant:
    variant_id: str
    label_pl: str
    description_pl: str
    preview_text: str
    preview_bg: str
    preview_fg: str
    usage_hint: str


VARIANTS: tuple[GicleeFrameVariant, ...] = (
    GicleeFrameVariant(
        variant_id="default_dark",
        label_pl="default / dark",
        description_pl="Domyślny znak na czarnym tle — luksusowy, minimalistyczny.",
        preview_text="GICLÉE FRAME™",
        preview_bg="#000000",
        preview_fg="#ffffff",
        usage_hint="Sekcje premium, stopka marki, ciemne bloki editorial.",
    ),
    GicleeFrameVariant(
        variant_id="light_inverted",
        label_pl="light / inverted",
        description_pl="Odwrócony kontrast — ciemny znak na jasnym tle sekcji.",
        preview_text="GICLÉE FRAME™",
        preview_bg="#f5f0e8",
        preview_fg="#1a1a1c",
        usage_hint="Jasne sekcje produktowe, passe-partout, galeria na białym.",
    ),
    GicleeFrameVariant(
        variant_id="compact",
        label_pl="compact",
        description_pl="Mniejsza typografia, zwięzły podpis — bez utraty charakteru.",
        preview_text="GICLÉE FRAME™",
        preview_bg="#000000",
        preview_fg="#ffffff",
        usage_hint="Karty produktu, meta-linia pod tytułem, wąskie kolumny.",
    ),
    GicleeFrameVariant(
        variant_id="section_label",
        label_pl="section-label",
        description_pl="Etykieta sekcji — dyskretny separator treści editorial.",
        preview_text="GICLÉE FRAME™",
        preview_bg="#000000",
        preview_fg="#c9a962",
        usage_hint="Nagłówki sekcji na stronie głównej, bloki „jak to działa”.",
    ),
    GicleeFrameVariant(
        variant_id="hero_label",
        label_pl="hero-label",
        description_pl="Wariant hero — większa obecność, nadal bez krzyku.",
        preview_text="GICLÉE FRAME™",
        preview_bg="#000000",
        preview_fg="#ffffff",
        usage_hint="Hero strony produktowej, intro marki, pierwszy ekran.",
    ),
)

VISUAL_RULES: tuple[str, ...] = (
    "Czarne tło (lub odwrócone: jasne tło + ciemny tekst)",
    "Biały lub kremowy tekst — wysoki kontrast, czytelność",
    "Minimalistyczny luksusowy znak — bez ozdobników",
    "Museum-quality · editorial · Awwwards minimalism",
    "Bez neonów, bez glitch, bez taniego badge'a",
    "Bez SaaS/startup look, bez gaming logo",
)

MOTION_RULES: tuple[str, ...] = (
    "Wejście: opacity 0 → 1",
    "Minimalny translateY (kilka px, nie więcej)",
    "Bardzo subtelny letter-spacing reveal",
    "prefers-reduced-motion: wyłącz animację lub tylko opacity",
    "Bez agresywnego motion, bez bounce/elastic",
)

PLACEMENT_SUGGESTIONS: tuple[str, ...] = (
    "Strona główna — hero lub section label przy bloku technologii ramy",
    "Strona produktu Giclée Frame — intro / hero-label",
    "Sekcje „jak powstaje oprawa” — section-label",
    "Stopka marki — compact / default dark",
)

AVOID_LIST: tuple[str, ...] = (
    "Koszyk, checkout, panel administracyjny",
    "Neon, glitch, pulsujące badge'e",
    "SaaS-style pill badges, gaming aesthetics",
    "Nadmierna animacja lub parallax na znaku",
    "Zapis/sync/deploy przed osobną akceptacją fazy Shopify",
)

_VARIANT_BY_ID: dict[str, GicleeFrameVariant] = {v.variant_id: v for v in VARIANTS}


def variant_by_id(variant_id: str | None) -> GicleeFrameVariant | None:
    if not variant_id:
        return None
    return _VARIANT_BY_ID.get(variant_id.strip())


def variant_menu_options() -> list[tuple[str, str]]:
    return [(v.variant_id, v.label_pl) for v in VARIANTS]


def visual_rules_display() -> list[tuple[str, str]]:
    return [(f"{i + 1}.", rule) for i, rule in enumerate(VISUAL_RULES)]


def motion_rules_display() -> list[tuple[str, str]]:
    return [(f"{i + 1}.", rule) for i, rule in enumerate(MOTION_RULES)]


def status_strip() -> str:
    return STATUS_STRIP
