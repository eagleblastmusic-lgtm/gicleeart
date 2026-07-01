"""Ustawienia użytkownika dashboardu (meta SQLite + .env)."""

from __future__ import annotations

import json
from typing import Any

from . import storage
from .privacy import hash_identifier

_SETTINGS_KEY = "user_settings"

_DEFAULTS: dict[str, Any] = {
    "exclude_visitor_hashes": [],
    "exclude_ip_hashes": [],
    "exclude_labels": {},
    "exclusions_enabled": True,
    "my_ip": "",
    "exclude_my_ip": False,
    "utm_templates": [
        {
            "name": "Instagram — launch",
            "utm_source": "instagram",
            "utm_medium": "social",
            "utm_campaign": "launch",
            "path": "/products/",
        },
        {
            "name": "Facebook — reklama",
            "utm_source": "facebook",
            "utm_medium": "paid",
            "utm_campaign": "prospecting",
            "path": "/products/",
        },
        {
            "name": "Newsletter",
            "utm_source": "newsletter",
            "utm_medium": "email",
            "utm_campaign": "weekly",
            "path": "/",
        },
        {
            "name": "Google Ads",
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "brand",
            "path": "/collections/",
        },
    ],
    "d1_retention_days": 90,
}


def _load_raw() -> dict[str, Any]:
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT value FROM analytics_meta WHERE key = ?",
            (_SETTINGS_KEY,),
        ).fetchone()
    if not row or not row["value"]:
        return dict(_DEFAULTS)
    try:
        data = json.loads(row["value"])
    except json.JSONDecodeError:
        return dict(_DEFAULTS)
    if not isinstance(data, dict):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(data)
    if not merged.get("utm_templates"):
        merged["utm_templates"] = list(_DEFAULTS["utm_templates"])
    if not isinstance(merged.get("exclude_labels"), dict):
        merged["exclude_labels"] = {}
    return merged


def _save_raw(data: dict[str, Any]) -> None:
    with storage.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO analytics_meta(key, value) VALUES (?, ?)",
            (_SETTINGS_KEY, json.dumps(data, ensure_ascii=False)),
        )


def _resolve_my_ip_and_hash(data: dict[str, Any]) -> tuple[str, str]:
    """Zwraca (my_ip, ip_hash) z pól my_ip lub etykiet IP: … w wykluczeniach."""
    my_ip = str(data.get("my_ip") or "").strip()
    ips = list(data.get("exclude_ip_hashes") or [])
    labels = dict(data.get("exclude_labels") or {})
    if my_ip:
        ih = hash_identifier(my_ip, prefix="ip")
        if ih:
            return my_ip, ih
    for ih in ips:
        label = labels.get(ih, "")
        if not isinstance(label, str) or not label.startswith("IP: "):
            continue
        candidate = label[4:].strip()
        if candidate and hash_identifier(candidate, prefix="ip") == ih:
            return candidate, ih
    return "", ""


def _enrich_settings(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    my_ip, ih = _resolve_my_ip_and_hash(out)
    if my_ip:
        out["my_ip"] = my_ip
        out["my_ip_hash"] = ih
        out["exclude_my_ip"] = bool(ih in list(out.get("exclude_ip_hashes") or []))
    else:
        out["my_ip_hash"] = ""
        out["exclude_my_ip"] = False
    return out


def get_settings() -> dict[str, Any]:
    return _enrich_settings(_load_raw())


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    cur = _load_raw()
    for key, val in patch.items():
        if key in _DEFAULTS:
            cur[key] = val
    _save_raw(cur)
    return cur


def exclusions_enabled() -> bool:
    return bool(_load_raw().get("exclusions_enabled", True))


def _raw_exclusions() -> tuple[list[str], list[str]]:
    s = _load_raw()
    return (
        list(s.get("exclude_visitor_hashes") or []),
        list(s.get("exclude_ip_hashes") or []),
    )


def get_exclusions() -> tuple[list[str], list[str]]:
    if not exclusions_enabled():
        return [], []
    return _raw_exclusions()


def _label_for_visitor(visitor_id: str) -> str:
    v = visitor_id.strip()
    if len(v) > 16:
        return f"Visitor: {v[:8]}…{v[-4:]}"
    return f"Visitor: {v}" if v else "Visitor"


def _label_for_ip(ip: str) -> str:
    return f"IP: {ip.strip()}" if ip.strip() else "IP"


def add_exclusion(
    *,
    visitor_id: str = "",
    ip: str = "",
    visitor_hash: str = "",
) -> dict[str, Any]:
    visitor_id = (visitor_id or "").strip()
    ip = (ip or "").strip()
    visitor_hash = (visitor_hash or "").strip()
    if not visitor_id and not ip and not visitor_hash:
        raise ValueError("Podaj Visitor ID lub publiczne IP")

    cur = _load_raw()
    visitors: list[str] = list(cur.get("exclude_visitor_hashes") or [])
    ips: list[str] = list(cur.get("exclude_ip_hashes") or [])
    labels: dict[str, str] = dict(cur.get("exclude_labels") or {})
    added: list[str] = []

    if visitor_hash:
        if visitor_hash not in visitors:
            visitors.append(visitor_hash)
            labels[visitor_hash] = f"Visitor: {visitor_hash[:12]}…"
            added.append("visitor")
        else:
            added.append("visitor_duplicate")
    elif visitor_id:
        vh = hash_identifier(visitor_id, prefix="v")
        if vh and vh not in visitors:
            visitors.append(vh)
            labels[vh] = _label_for_visitor(visitor_id)
            added.append("visitor")
        elif vh:
            added.append("visitor_duplicate")
    if ip:
        ih = hash_identifier(ip, prefix="ip")
        if ih and ih not in ips:
            ips.append(ih)
            labels[ih] = _label_for_ip(ip)
            added.append("ip")
        elif ih:
            added.append("ip_duplicate")
        if not cur.get("my_ip"):
            cur["my_ip"] = ip

    if not any(x in added for x in ("visitor", "ip")):
        raise ValueError("Te wykluczenia są już na liście")

    cur["exclude_visitor_hashes"] = visitors
    cur["exclude_ip_hashes"] = ips
    cur["exclude_labels"] = labels
    _save_raw(cur)
    return get_settings()


def _auto_exclude_recent_test_visitors(
    cur: dict[str, Any],
    *,
    min_events: int = 2,
    limit: int = 10,
) -> int:
    """Gdy brak IP w bazie — dołącz top visitorów (pewnie testy właściciela)."""
    from datetime import datetime, timedelta, timezone

    since = (
        datetime.now(timezone.utc) - timedelta(days=14)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT visitor_id_hash, COUNT(*) AS events
            FROM analytics_events
            WHERE bot_suspected = 0 AND created_at >= ?
            GROUP BY visitor_id_hash
            ORDER BY events DESC, visitor_id_hash
            LIMIT ?
            """,
            (since, limit),
        ).fetchall()

    visitors: list[str] = list(cur.get("exclude_visitor_hashes") or [])
    labels: dict[str, str] = dict(cur.get("exclude_labels") or {})
    added = 0
    for row in rows:
        vh = str(row["visitor_id_hash"] or "").strip()
        if not vh or vh in visitors:
            continue
        if int(row["events"] or 0) < min_events:
            continue
        visitors.append(vh)
        labels[vh] = f"Visitor (auto): {vh[:12]}…"
        added += 1
    cur["exclude_visitor_hashes"] = visitors
    cur["exclude_labels"] = labels
    return added


def toggle_my_ip(*, ip: str = "", enabled: bool = True) -> dict[str, Any]:
    """Włącza/wyłącza wykluczenie zapisanego publicznego IP (suwak w dashboardzie)."""
    ip = (ip or "").strip()
    cur = _load_raw()
    my_ip = str(cur.get("my_ip") or "").strip()
    ips: list[str] = list(cur.get("exclude_ip_hashes") or [])
    labels: dict[str, str] = dict(cur.get("exclude_labels") or {})

    if enabled:
        if not ip:
            raise ValueError("Brak adresu IP — użyj „Pobierz moje IP” lub wpisz ręcznie")
        ih = hash_identifier(ip, prefix="ip")
        if not ih:
            raise ValueError("Nieprawidłowy adres IP")
        cur["my_ip"] = ip
        cur["exclude_my_ip"] = True
        cur["exclusions_enabled"] = True
        if ih not in ips:
            ips.append(ih)
        labels[ih] = _label_for_ip(ip)
        impact = storage.count_exclusion_impact()
        if int(impact.get("events_with_ip") or 0) == 0:
            _auto_exclude_recent_test_visitors(cur)
    else:
        resolved_ip, ih = _resolve_my_ip_and_hash(cur)
        if not ih and ip:
            resolved_ip = ip
            ih = hash_identifier(ip, prefix="ip")
        cur["exclude_my_ip"] = False
        if ih and ih in ips:
            ips.remove(ih)
            labels.pop(ih, None)
        if resolved_ip:
            cur["my_ip"] = resolved_ip

    cur["exclude_ip_hashes"] = ips
    cur["exclude_labels"] = labels
    _save_raw(cur)
    return get_settings()


def remove_exclusion(*, kind: str, hash_value: str) -> dict[str, Any]:
    kind = (kind or "").strip().lower()
    hash_value = (hash_value or "").strip()
    if not hash_value:
        raise ValueError("Brak identyfikatora wykluczenia")

    cur = _load_raw()
    labels: dict[str, str] = dict(cur.get("exclude_labels") or {})

    if kind == "visitor":
        visitors = [v for v in cur.get("exclude_visitor_hashes") or [] if v != hash_value]
        if len(visitors) == len(cur.get("exclude_visitor_hashes") or []):
            raise ValueError("Nie znaleziono wykluczenia visitor")
        cur["exclude_visitor_hashes"] = visitors
    elif kind == "ip":
        ips = [i for i in cur.get("exclude_ip_hashes") or [] if i != hash_value]
        if len(ips) == len(cur.get("exclude_ip_hashes") or []):
            raise ValueError("Nie znaleziono wykluczenia IP")
        cur["exclude_ip_hashes"] = ips
        my_ip = str(cur.get("my_ip") or "").strip()
        if my_ip and hash_identifier(my_ip, prefix="ip") == hash_value:
            cur["exclude_my_ip"] = False
    else:
        raise ValueError("Nieprawidłowy typ wykluczenia")

    labels.pop(hash_value, None)
    cur["exclude_labels"] = labels
    _save_raw(cur)
    return get_settings()


def set_last_sync(iso: str) -> None:
    with storage.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO analytics_meta(key, value) VALUES (?, ?)",
            ("last_worker_sync_at", iso),
        )


def get_last_sync() -> str | None:
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT value FROM analytics_meta WHERE key = ?",
            ("last_worker_sync_at",),
        ).fetchone()
    return str(row["value"]) if row and row["value"] else None


def build_utm_url(
    *,
    base_domain: str,
    path: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
    utm_content: str = "",
    utm_term: str = "",
) -> str:
    from urllib.parse import urlencode

    domain = base_domain.strip().rstrip("/")
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    p = path if path.startswith("/") else f"/{path}"
    params = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
    }
    if utm_content:
        params["utm_content"] = utm_content
    if utm_term:
        params["utm_term"] = utm_term
    return f"{domain}{p}?{urlencode(params)}"
