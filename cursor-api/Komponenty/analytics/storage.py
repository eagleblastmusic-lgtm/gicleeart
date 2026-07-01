"""SQLite — eventy, sesje i metryki zagregowane."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import env_config

_LOCK = threading.Lock()
_SCHEMA_VERSION = 2

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'standard',
    shopify_event_id TEXT,
    visitor_id_hash TEXT NOT NULL,
    session_id TEXT NOT NULL,
    customer_id_hash TEXT,
    shopify_customer_id_hash TEXT,
    shopify_order_id TEXT,
    shopify_product_id TEXT,
    shopify_variant_id TEXT,
    product_title TEXT,
    collection_id TEXT,
    url TEXT,
    path TEXT,
    page_title TEXT,
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    utm_term TEXT,
    device_type TEXT,
    browser TEXT,
    os TEXT,
    country TEXT,
    region TEXT,
    language TEXT,
    currency TEXT,
    cart_value REAL,
    checkout_value REAL,
    order_value REAL,
    quantity INTEGER,
    metadata_json TEXT,
    consent_status TEXT,
    bot_suspected INTEGER NOT NULL DEFAULT 0,
    source_bucket TEXT,
    ip_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_event_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_visitor_hash ON analytics_events(visitor_id_hash);
CREATE INDEX IF NOT EXISTS idx_events_product_id ON analytics_events(shopify_product_id);
CREATE INDEX IF NOT EXISTS idx_events_order_id ON analytics_events(shopify_order_id);
CREATE INDEX IF NOT EXISTS idx_events_country ON analytics_events(country);
CREATE INDEX IF NOT EXISTS idx_events_utm_source ON analytics_events(utm_source);
CREATE INDEX IF NOT EXISTS idx_events_utm_campaign ON analytics_events(utm_campaign);

CREATE TABLE IF NOT EXISTS analytics_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    visitor_id_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    landing_page TEXT,
    exit_page TEXT,
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    device_type TEXT,
    country TEXT,
    pageviews_count INTEGER NOT NULL DEFAULT 0,
    events_count INTEGER NOT NULL DEFAULT 0,
    products_viewed_count INTEGER NOT NULL DEFAULT 0,
    add_to_cart_count INTEGER NOT NULL DEFAULT 0,
    checkout_started INTEGER NOT NULL DEFAULT 0,
    purchase_completed INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0,
    order_id TEXT,
    source_bucket TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_first_seen ON analytics_sessions(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_sessions_country ON analytics_sessions(country);

CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    visitors INTEGER NOT NULL DEFAULT 0,
    sessions INTEGER NOT NULL DEFAULT 0,
    pageviews INTEGER NOT NULL DEFAULT 0,
    entrances INTEGER NOT NULL DEFAULT 0,
    product_views INTEGER NOT NULL DEFAULT 0,
    add_to_carts INTEGER NOT NULL DEFAULT 0,
    checkouts_started INTEGER NOT NULL DEFAULT 0,
    purchases INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0,
    conversion_rate REAL NOT NULL DEFAULT 0,
    add_to_cart_rate REAL NOT NULL DEFAULT 0,
    checkout_conversion_rate REAL NOT NULL DEFAULT 0,
    average_order_value REAL NOT NULL DEFAULT 0,
    bounce_rate REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analytics_country_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    country TEXT NOT NULL,
    visitors INTEGER NOT NULL DEFAULT 0,
    sessions INTEGER NOT NULL DEFAULT 0,
    pageviews INTEGER NOT NULL DEFAULT 0,
    entrances INTEGER NOT NULL DEFAULT 0,
    product_views INTEGER NOT NULL DEFAULT 0,
    add_to_carts INTEGER NOT NULL DEFAULT 0,
    checkouts_started INTEGER NOT NULL DEFAULT 0,
    purchases INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0,
    conversion_rate REAL NOT NULL DEFAULT 0,
    add_to_cart_rate REAL NOT NULL DEFAULT 0,
    average_order_value REAL NOT NULL DEFAULT 0,
    bounce_rate REAL NOT NULL DEFAULT 0,
    UNIQUE(date, country)
);

CREATE TABLE IF NOT EXISTS analytics_product_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    shopify_product_id TEXT NOT NULL,
    product_title TEXT,
    views INTEGER NOT NULL DEFAULT 0,
    add_to_carts INTEGER NOT NULL DEFAULT 0,
    checkouts INTEGER NOT NULL DEFAULT 0,
    purchases INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0,
    conversion_rate REAL NOT NULL DEFAULT 0,
    add_to_cart_rate REAL NOT NULL DEFAULT 0,
    UNIQUE(date, shopify_product_id)
);

CREATE TABLE IF NOT EXISTS analytics_attribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,
    session_id TEXT,
    visitor_id_hash TEXT,
    first_touch_source TEXT,
    first_touch_medium TEXT,
    first_touch_campaign TEXT,
    last_touch_source TEXT,
    last_touch_medium TEXT,
    last_touch_campaign TEXT,
    landing_page TEXT,
    conversion_path_json TEXT,
    revenue REAL NOT NULL DEFAULT 0,
    country TEXT,
    match_type TEXT NOT NULL DEFAULT 'exact',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attr_order ON analytics_attribution(order_id);

CREATE TABLE IF NOT EXISTS analytics_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _ensure_db_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = env_config.db_path()
    _ensure_db_dir(path)
    with _LOCK:
        conn = sqlite3.connect(str(path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_CREATE_SQL)
        _migrate_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO analytics_meta(key, value) VALUES (?, ?)",
            ("schema_version", str(_SCHEMA_VERSION)),
        )


def _migrate_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(analytics_events)")}
    if "ip_hash" not in cols:
        conn.execute("ALTER TABLE analytics_events ADD COLUMN ip_hash TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_ip_hash ON analytics_events(ip_hash)"
    )
    row = conn.execute(
        "SELECT value FROM analytics_meta WHERE key = ?",
        ("schema_version",),
    ).fetchone()
    try:
        version = int(row["value"]) if row and row["value"] else 1
    except ValueError:
        version = 1
    if version < 2:
        conn.execute(
            """
            UPDATE analytics_events
            SET ip_hash = json_extract(metadata_json, '$.ip_hash')
            WHERE (ip_hash IS NULL OR ip_hash = '')
              AND metadata_json LIKE '%ip_hash%'
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO analytics_meta(key, value) VALUES (?, ?)",
            ("schema_version", "2"),
        )


def event_exists(event_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM analytics_events WHERE event_id = ? LIMIT 1",
            (event_id,),
        ).fetchone()
        return row is not None


def count_session_events(session_id: str, since_iso: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM analytics_events
            WHERE session_id = ? AND created_at >= ? AND bot_suspected = 0
            """,
            (session_id, since_iso),
        ).fetchone()
        return int(row["c"]) if row else 0


def insert_event(row: dict[str, Any]) -> int:
    cols = [
        "event_id", "event_name", "event_type", "shopify_event_id",
        "visitor_id_hash", "session_id", "customer_id_hash", "shopify_customer_id_hash",
        "shopify_order_id", "shopify_product_id", "shopify_variant_id", "product_title",
        "collection_id", "url", "path", "page_title", "referrer",
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "device_type", "browser", "os", "country", "region", "language", "currency",
        "cart_value", "checkout_value", "order_value", "quantity", "metadata_json",
        "consent_status", "bot_suspected", "source_bucket", "ip_hash", "created_at",
    ]
    placeholders = ", ".join("?" for _ in cols)
    names = ", ".join(cols)
    values = [row.get(c) for c in cols]
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO analytics_events ({names}) VALUES ({placeholders})",
            values,
        )
        return int(cur.lastrowid or 0)


def get_session(session_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM analytics_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_session(session_id: str, patch: dict[str, Any]) -> None:
    with connect() as conn:
        existing = conn.execute(
            "SELECT * FROM analytics_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if existing is None:
            cols = ["session_id"] + list(patch.keys())
            vals = [session_id] + [patch[k] for k in patch]
            conn.execute(
                f"INSERT INTO analytics_sessions ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                vals,
            )
            return
        sets = ", ".join(f"{k} = ?" for k in patch)
        vals = list(patch.values()) + [session_id]
        conn.execute(
            f"UPDATE analytics_sessions SET {sets} WHERE session_id = ?",
            vals,
        )


def query_events(
    *,
    date_from: str,
    date_to: str,
    country: str | None = None,
    device: str | None = None,
    source: str | None = None,
    exclude_bots: bool = True,
    exclude_visitor_hashes: list[str] | None = None,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    sql = """
        SELECT * FROM analytics_events
        WHERE created_at >= ? AND created_at < ?
    """
    params: list[Any] = [date_from, date_to]
    if exclude_bots:
        sql += " AND bot_suspected = 0"
    if country:
        sql += " AND country = ?"
        params.append(country.upper())
    if device:
        sql += " AND device_type = ?"
        params.append(device)
    if source:
        sql += " AND source_bucket = ?"
        params.append(source)
    if exclude_visitor_hashes:
        placeholders = ", ".join("?" for _ in exclude_visitor_hashes)
        sql += f" AND visitor_id_hash NOT IN ({placeholders})"
        params.extend(exclude_visitor_hashes)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        out = [dict(r) for r in rows]

    from . import settings as _settings

    vis_ex, ip_ex = _settings.get_exclusions()
    combined_vis = set(exclude_visitor_hashes or []) | set(vis_ex)
    if combined_vis:
        out = [e for e in out if e.get("visitor_id_hash") not in combined_vis]
    if ip_ex:
        out = [e for e in out if not _event_has_excluded_ip(e, ip_ex)]
        blocked_sessions = _blocked_session_ids_for_ips(
            ip_ex, date_from=date_from, date_to=date_to
        )
        if blocked_sessions:
            out = [
                e for e in out
                if str(e.get("session_id") or "") not in blocked_sessions
            ]
    return out


def _event_has_excluded_ip(event: dict[str, Any], exclude_ips: list[str]) -> bool:
    direct = (event.get("ip_hash") or "").strip()
    if direct and direct in exclude_ips:
        return True
    import json

    raw = event.get("metadata_json") or ""
    if not raw:
        return False
    try:
        meta = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return False
    ip_hash = meta.get("ip_hash") if isinstance(meta, dict) else None
    return bool(ip_hash and ip_hash in exclude_ips)


def _blocked_session_ids_for_ips(
    ip_ex: list[str],
    *,
    date_from: str,
    date_to: str,
) -> set[str]:
    if not ip_ex:
        return set()
    blocked: set[str] = set()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT session_id, ip_hash, metadata_json FROM analytics_events
            WHERE bot_suspected = 0 AND created_at >= ? AND created_at < ?
            """,
            (date_from, date_to),
        ).fetchall()
    for row in rows:
        ev = dict(row)
        if _event_has_excluded_ip(ev, ip_ex):
            sid = str(ev.get("session_id") or "").strip()
            if sid:
                blocked.add(sid)
    return blocked


def count_exclusion_impact() -> dict[str, Any]:
    from . import settings as _settings

    with connect() as conn:
        events_with_ip = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM analytics_events
                WHERE bot_suspected = 0
                  AND ip_hash IS NOT NULL AND ip_hash != ''
                """
            ).fetchone()["c"]
        )
        total_events = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM analytics_events WHERE bot_suspected = 0"
            ).fetchone()["c"]
        )

    if not _settings.exclusions_enabled():
        return {
            "enabled": False,
            "events": 0,
            "visitors": 0,
            "sessions": 0,
            "events_with_ip": events_with_ip,
            "total_events": total_events,
        }

    vis_ex, ip_ex = _settings._raw_exclusions()
    if not vis_ex and not ip_ex:
        return {
            "enabled": True,
            "events": 0,
            "visitors": 0,
            "sessions": 0,
            "events_with_ip": events_with_ip,
            "total_events": total_events,
        }

    vis_set = set(vis_ex)
    excluded_events = 0
    excluded_visitors: set[str] = set()
    excluded_sessions: set[str] = set()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT visitor_id_hash, session_id, ip_hash, metadata_json
            FROM analytics_events WHERE bot_suspected = 0
            """
        ).fetchall()
    for row in rows:
        ev = dict(row)
        matched = False
        vh = str(ev.get("visitor_id_hash") or "")
        if vh and vh in vis_set:
            matched = True
        if ip_ex and _event_has_excluded_ip(ev, ip_ex):
            matched = True
        if matched:
            excluded_events += 1
            if vh:
                excluded_visitors.add(vh)
            sid = str(ev.get("session_id") or "")
            if sid:
                excluded_sessions.add(sid)

    return {
        "enabled": True,
        "events": excluded_events,
        "visitors": len(excluded_visitors),
        "sessions": len(excluded_sessions),
        "events_with_ip": events_with_ip,
        "total_events": total_events,
    }


def suggest_recent_visitors(*, days: int = 14, limit: int = 8) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta, timezone

    from . import settings as _settings

    since = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT visitor_id_hash, COUNT(*) AS events,
                   MAX(created_at) AS last_seen,
                   MAX(country) AS country,
                   MAX(device_type) AS device_type
            FROM analytics_events
            WHERE bot_suspected = 0 AND created_at >= ?
            GROUP BY visitor_id_hash
            ORDER BY events DESC, last_seen DESC
            LIMIT ?
            """,
            (since, limit),
        ).fetchall()
    excluded_vis, _ = _settings._raw_exclusions()
    blocked = set(excluded_vis)
    return [
        {
            "visitor_id_hash": r["visitor_id_hash"],
            "events": int(r["events"]),
            "last_seen": r["last_seen"],
            "country": r["country"],
            "device_type": r["device_type"],
            "excluded": r["visitor_id_hash"] in blocked,
        }
        for r in rows
    ]


def query_sessions(
    *,
    date_from: str,
    date_to: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM analytics_sessions
            WHERE first_seen_at >= ? AND first_seen_at < ?
            ORDER BY last_seen_at DESC LIMIT ?
            """,
            (date_from, date_to, limit),
        ).fetchall()
        out = [dict(r) for r in rows]

    from . import settings as _settings

    vis_ex, ip_ex = _settings.get_exclusions()
    if vis_ex:
        blocked = set(vis_ex)
        out = [s for s in out if s.get("visitor_id_hash") not in blocked]
    if ip_ex:
        blocked_sessions = _blocked_session_ids_for_ips(
            ip_ex, date_from=date_from, date_to=date_to
        )
        if blocked_sessions:
            out = [s for s in out if s.get("session_id") not in blocked_sessions]
    return out


def delete_analytics(
    *,
    visitor_id_hash: str | None = None,
    session_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, int]:
    deleted = {"events": 0, "sessions": 0, "attribution": 0}
    with connect() as conn:
        if session_id:
            cur = conn.execute(
                "DELETE FROM analytics_events WHERE session_id = ?", (session_id,)
            )
            deleted["events"] = cur.rowcount
            cur = conn.execute(
                "DELETE FROM analytics_sessions WHERE session_id = ?", (session_id,)
            )
            deleted["sessions"] = cur.rowcount
        elif visitor_id_hash:
            cur = conn.execute(
                "DELETE FROM analytics_events WHERE visitor_id_hash = ?",
                (visitor_id_hash,),
            )
            deleted["events"] = cur.rowcount
            cur = conn.execute(
                "DELETE FROM analytics_sessions WHERE visitor_id_hash = ?",
                (visitor_id_hash,),
            )
            deleted["sessions"] = cur.rowcount
        elif date_from and date_to:
            cur = conn.execute(
                "DELETE FROM analytics_events WHERE created_at >= ? AND created_at < ?",
                (date_from, date_to),
            )
            deleted["events"] = cur.rowcount
            cur = conn.execute(
                "DELETE FROM analytics_sessions WHERE first_seen_at >= ? AND first_seen_at < ?",
                (date_from, date_to),
            )
            deleted["sessions"] = cur.rowcount
        conn.execute(
            "DELETE FROM analytics_attribution WHERE created_at >= ? AND created_at < ?",
            (date_from or "1970-01-01", date_to or "9999-12-31"),
        )
    return deleted


def stats_summary() -> dict[str, Any]:
    with connect() as conn:
        events = conn.execute("SELECT COUNT(*) AS c FROM analytics_events").fetchone()
        sessions = conn.execute("SELECT COUNT(*) AS c FROM analytics_sessions").fetchone()
        last = conn.execute(
            "SELECT MAX(created_at) AS m FROM analytics_events"
        ).fetchone()
        bots = conn.execute(
            "SELECT COUNT(*) AS c FROM analytics_events WHERE bot_suspected = 1"
        ).fetchone()
    return {
        "total_events": int(events["c"]) if events else 0,
        "total_sessions": int(sessions["c"]) if sessions else 0,
        "last_event_at": (last["m"] if last else None) or None,
        "bot_events": int(bots["c"]) if bots else 0,
        "db_path": str(env_config.db_path()),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
