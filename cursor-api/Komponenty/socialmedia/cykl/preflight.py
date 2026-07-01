"""Pre-flight check przed publikacja do Meta.

Sprawdzamy:
- Credentiale kanalu (token + page_id / ig_user_id) -> `check_credentials`.
- Caption: niepusty i w limicie znakow dla platformy.
- Obrazy: jest przynajmniej jeden obraz (lokalny plik lub CDN URL lub product_image_url).
- Link: jesli jest, parsuje sie do prawidlowego URL (http(s)://...).
- `scheduled_at`: jezeli jest, daje sie sparsowac do ISO.

Pre-flight NIE wykonuje zadnych zadan zdalnych (nie odpala Graph API).
Dzieki temu mozna nim sprawdzic caly queue szybko, bez pozywania limitow API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from . import platforms_cykl as _cp
from . import storage
from .meta_publisher import check_credentials

# Meta/Facebook limit caption: w praktyce liczy sie okolo 63k znakow dla FB,
# ale zdrowo jest trzymac znacznie mniej. Dla IG: caption do 2200 znakow.
_FB_CAPTION_LIMIT = 8000  # pragmatyczny miekki limit
_IG_CAPTION_LIMIT = 2200

_URL_RE = re.compile(r"https?://[^\s]+")


@dataclass
class PreflightCheck:
    name: str
    ok: bool
    message: str


@dataclass
class PreflightResult:
    channel: str
    ok: bool
    checks: list[PreflightCheck]


def preflight_for_channel(item: storage.CykleItem, channel_code: str) -> PreflightResult:
    """Zwraca wynik pre-flightu dla jednego kanalu."""
    checks: list[PreflightCheck] = []

    # 1) Credentiale
    ok, msg = check_credentials(channel_code)
    checks.append(PreflightCheck(
        name="credentials",
        ok=ok,
        message="OK" if ok else msg,
    ))

    # 2) Caption
    platform = "fb" if channel_code.startswith("fb") else "ig"
    lang = "pl" if channel_code.endswith("_pl") else "en"
    specific = getattr(item, f"caption_{platform}_{lang}", "") or ""
    fallback = getattr(item, f"caption_{lang}", "") or ""
    caption = (specific or fallback).strip()
    if not caption:
        checks.append(PreflightCheck("caption", False, "Brak captiona (pusty)."))
    else:
        limit = _IG_CAPTION_LIMIT if platform == "ig" else _FB_CAPTION_LIMIT
        n = len(caption)
        if n > limit:
            checks.append(PreflightCheck(
                "caption_limit", False,
                f"Caption {n} znakow > limit {limit} dla {platform.upper()}",
            ))
        else:
            checks.append(PreflightCheck("caption_limit", True, f"{n} znakow (limit {limit})"))

    # 3) Obrazy
    has_image = bool(_any_image_for(item, platform))
    checks.append(PreflightCheck(
        name="images",
        ok=has_image,
        message="OK" if has_image else "Brak obrazow (ani lokalny, ani CDN, ani produkt).",
    ))

    # 4) Link w caption (opcjonalny, informacyjny)
    link_ok, link_msg = _check_links_in_caption(caption)
    checks.append(PreflightCheck(
        name="links",
        ok=link_ok,
        message=link_msg,
    ))

    # 5) scheduled_at
    sched = (item.scheduled_at or "").strip()
    if sched:
        try:
            datetime.fromisoformat(sched)
            checks.append(PreflightCheck("scheduled_at", True, sched))
        except ValueError:
            checks.append(PreflightCheck(
                "scheduled_at", False,
                f"Niepoprawny format daty: {sched!r}",
            ))
    else:
        checks.append(PreflightCheck(
            "scheduled_at", True, "(brak daty — publikacja reczna)",
        ))

    # Wynik: blokery to credentials, images, caption (pusty lub przekracza limit)
    blocker_names = {"credentials", "images", "caption", "caption_limit"}
    ok = all(c.ok for c in checks if c.name in blocker_names)
    return PreflightResult(
        channel=channel_code,
        ok=ok,
        checks=checks,
    )


def preflight_item(
    item: storage.CykleItem,
    channels: Iterable[str] | None = None,
) -> list[PreflightResult]:
    chans = list(channels) if channels else list(item.channels_enabled) or list(_cp.CHANNEL_ORDER)
    return [preflight_for_channel(item, ch) for ch in chans]


def summarize_result(result: PreflightResult) -> str:
    """Zwraca tresc do pokazania w toastcie / raporcie."""
    if result.ok:
        return f"{result.channel}: ✅ OK"
    bad = [c for c in result.checks if not c.ok]
    msgs = "; ".join(f"{c.name}: {c.message}" for c in bad)
    return f"{result.channel}: ⚠ {msgs}"


def _any_image_for(item: storage.CykleItem, platform: str) -> bool:
    # Priorytet: platformowe > ogolne > z sklepu
    plat_main = getattr(item, f"image_{platform}_main", "") or ""
    plat_main_cdn = getattr(item, f"cdn_{platform}_main", "") or ""
    if plat_main or plat_main_cdn:
        if plat_main and not _looks_like_url(plat_main):
            # lokalna sciezka - sprawdz istnienie
            p = Path(plat_main)
            if not p.is_absolute():
                p = storage.images_dir() / plat_main
            if not p.is_file():
                return bool(plat_main_cdn)
        return True
    if item.image_main or item.cdn_main:
        return True
    if item.product_image_url:
        return True
    return False


def _check_links_in_caption(caption: str) -> tuple[bool, str]:
    links = _URL_RE.findall(caption or "")
    if not links:
        return True, "(brak linkow)"
    bad = []
    for u in links:
        if not (u.startswith("http://") or u.startswith("https://")):
            bad.append(u)
            continue
        if " " in u or "\n" in u:
            bad.append(u)
    if bad:
        return False, f"Zle linki: {', '.join(bad[:3])}"
    return True, f"{len(links)} link(ow) OK"


def _looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")
