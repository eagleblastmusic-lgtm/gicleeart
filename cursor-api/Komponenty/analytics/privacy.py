"""Anonimizacja i RODO — bez pełnego IP."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any

_HASH_SALT_ENV = "ANALYTICS_HASH_SALT"


def _salt() -> bytes:
    raw = (os.environ.get(_HASH_SALT_ENV) or "giclee-analytics").encode("utf-8")
    return raw


def hash_identifier(value: str, *, prefix: str = "v") -> str:
    """SHA-256 z solą — nieodwracalny identyfikator odwiedzającego/sesji."""
    clean = (value or "").strip()
    if not clean:
        return ""
    digest = hashlib.sha256(_salt() + clean.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def hash_customer_id(customer_id: str | int | None) -> str:
    if customer_id is None:
        return ""
    return hash_identifier(str(customer_id), prefix="c")


def ip_country_hint(headers: dict[str, str]) -> str:
    """Kraj z nagłówków edge (Cloudflare / Vercel) — bez zapisu IP."""
    for key in ("cf-ipcountry", "x-vercel-ip-country", "cloudfront-viewer-country"):
        val = (headers.get(key) or headers.get(key.upper()) or "").strip().upper()
        if val and val != "XX" and len(val) == 2:
            return val
    return ""


def ip_hash_for_rate_limit(ip: str) -> str:
    """Jednokierunkowy hash IP wyłącznie do rate limitu — nie trafia do bazy eventów."""
    if not ip:
        return ""
    return hashlib.sha256(_salt() + ip.encode("utf-8")).hexdigest()[:16]


def consent_allows_tracking(consent_status: str) -> bool:
    s = (consent_status or "").strip().lower()
    if not s:
        return True
    if s in {"denied", "reject", "rejected", "opt_out", "no"}:
        return False
    return s in {"granted", "accept", "accepted", "yes", "marketing", "analytics"}


def sanitize_metadata(meta: dict[str, Any], *, max_bytes: int = 4096) -> str:
    import json

    safe: dict[str, Any] = {}
    blocked = re.compile(r"(email|phone|address|password|token|secret)", re.I)
    for k, v in meta.items():
        if blocked.search(str(k)):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe[str(k)[:64]] = v
        elif isinstance(v, list):
            safe[str(k)[:64]] = [x for x in v[:20] if isinstance(x, (str, int, float, bool))]
    raw = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > max_bytes:
        return raw.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return raw


def verify_collect_secret(provided: str, expected: str) -> bool:
    if not expected:
        return False
    return hmac.compare_digest((provided or "").strip(), expected.strip())
