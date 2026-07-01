"""Klasyfikacja źródeł ruchu (UTM + referrer)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

SOCIAL_HOSTS = re.compile(
    r"(facebook\.com|fb\.com|instagram\.com|tiktok\.com|twitter\.com|x\.com|"
    r"linkedin\.com|pinterest\.|youtube\.com|t\.co)",
    re.I,
)
SEARCH_HOSTS = re.compile(
    r"(google\.|bing\.com|duckduckgo\.|yahoo\.|ecosia\.|yandex\.)",
    re.I,
)
PAID_MEDIUMS = re.compile(r"(cpc|ppc|paid|ads|display|retarget)", re.I)
EMAIL_MEDIUMS = re.compile(r"(email|newsletter|mail)", re.I)


def classify_source(
    *,
    referrer: str = "",
    utm_source: str = "",
    utm_medium: str = "",
) -> str:
    medium = (utm_medium or "").strip().lower()
    source = (utm_source or "").strip().lower()
    ref = (referrer or "").strip()

    if medium and PAID_MEDIUMS.search(medium):
        return "paid"
    if medium and EMAIL_MEDIUMS.search(medium):
        return "email"
    if medium == "social" or (source and SOCIAL_HOSTS.search(source)):
        return "social"
    if medium in {"organic", "seo"}:
        return "organic_search"

    if ref:
        try:
            host = urlparse(ref).netloc.lower()
        except Exception:
            host = ""
        if not host:
            return "direct"
        if SEARCH_HOSTS.search(host):
            return "organic_search"
        if SOCIAL_HOSTS.search(host):
            return "social"
        if "gicleeart" in host:
            return "direct"
        return "referral"

    if not source and not medium:
        return "direct"
    if source and SEARCH_HOSTS.search(source):
        return "organic_search"
    if source:
        return "referral"
    return "unknown"


def parse_utm_from_url(url: str) -> dict[str, str]:
    from urllib.parse import parse_qs, urlparse

    try:
        qs = parse_qs(urlparse(url).query)
    except Exception:
        return {}
    out: dict[str, str] = {}
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        vals = qs.get(key) or []
        if vals:
            out[key] = str(vals[0])[:200]
    return out
