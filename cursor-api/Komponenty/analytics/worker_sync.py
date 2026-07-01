"""Pobieranie eventów z Cloudflare Worker (D1) do lokalnej bazy SQLite."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .env_config import collect_secret, worker_base_url
from . import sessions, settings, storage


class WorkerSyncError(Exception):
    pass


_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _base_url() -> str:
    base = worker_base_url()
    if not base:
        raise WorkerSyncError(
            "Ustaw ANALYTICS_COLLECT_URL w .env (np. https://…workers.dev/api/analytics/collect)"
        )
    return base.rstrip("/")


def _worker_headers(secret: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "X-Analytics-Secret": secret,
        "User-Agent": _BROWSER_UA,
    }


def _fetch_export(*, since: str | None = None, limit: int = 10000) -> list[dict[str, Any]]:
    secret = collect_secret()
    if not secret:
        raise WorkerSyncError("Brak ANALYTICS_COLLECT_SECRET w .env")

    url = f"{_base_url()}/api/analytics/export?limit={limit}"
    if since:
        url += f"&since={urllib.parse.quote(since)}"

    req = urllib.request.Request(url, headers=_worker_headers(secret), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise WorkerSyncError(f"Worker HTTP {e.code}: {detail[:400]}") from e
    except urllib.error.URLError as e:
        raise WorkerSyncError(f"Brak połączenia z Workerem: {e}") from e

    data = json.loads(raw) if raw else {}
    if not data.get("ok"):
        raise WorkerSyncError(str(data.get("error") or "Export failed"))
    events = data.get("events") or []
    if not isinstance(events, list):
        return []
    return events


_SYNC_CURSOR_KEY = "worker_sync_cursor"
_EPOCH = "1970-01-01T00:00:00.000Z"


def _get_sync_cursor() -> str:
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT value FROM analytics_meta WHERE key = ?",
            (_SYNC_CURSOR_KEY,),
        ).fetchone()
    if row and row["value"]:
        return str(row["value"])
    return _EPOCH


def _set_sync_cursor(iso: str) -> None:
    with storage.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO analytics_meta(key, value) VALUES (?, ?)",
            (_SYNC_CURSOR_KEY, iso),
        )


def _cloud_ahead_of_local() -> bool:
    """Chmura ma więcej eventów niż lokalna baza — wymusza backfill."""
    try:
        stats = worker_stats()
    except Exception:
        return False
    if not stats.get("ok"):
        return False
    cloud = int(stats.get("total_events") or 0)
    local = int(storage.stats_summary().get("total_events") or 0)
    return cloud > local


def _shop_event_timestamps(events: list[dict[str, Any]]) -> list[str]:
    """Timestamps eventów sklepu (pomija lokalne testy diag_/test_ z przyszłym czasem)."""
    out: list[str] = []
    for row in events:
        eid = str(row.get("event_id") or "")
        if eid.startswith(("diag_", "test_")):
            continue
        ts = str(row.get("created_at") or "")
        if ts:
            out.append(ts)
    return out


def _update_sync_cursor_from_batch(events: list[dict[str, Any]]) -> None:
    ts_list = _shop_event_timestamps(events)
    if not ts_list:
        return
    max_ts = max(ts_list)
    cur = _get_sync_cursor()
    # Zatruty kursor (np. test diag z 21:15 UTC) — cofnij do realnego ruchu sklepu
    if cur > max_ts and cur >= "2026-06-15T20:00:00":
        _set_sync_cursor(max_ts)
        return
    if max_ts > cur:
        _set_sync_cursor(max_ts)


def pull_from_worker(*, since: str | None = None) -> dict[str, Any]:
    """Import eventów z D1 → lokalny SQLite (deduplikacja po event_id)."""
    backfill = False
    if since:
        since_iso = since
    elif _cloud_ahead_of_local():
        since_iso = _EPOCH
        backfill = True
    else:
        since_iso = _get_sync_cursor()

    events = _fetch_export(since=since_iso)

    inserted = 0
    skipped = 0
    new_rows: list[dict] = []
    exclude_visitors, exclude_ips = settings.get_exclusions()

    for row in events:
        eid = str(row.get("event_id") or "").strip()
        if not eid or storage.event_exists(eid):
            skipped += 1
            continue
        payload = dict(row)
        payload.pop("id", None)
        vhash = str(payload.get("visitor_id_hash") or "")
        if vhash and vhash in exclude_visitors:
            skipped += 1
            continue
        if exclude_ips and storage._event_has_excluded_ip(payload, exclude_ips):
            skipped += 1
            continue
        ip_hash = (payload.get("ip_hash") or "").strip()
        if not ip_hash:
            meta_raw = payload.get("metadata_json")
            if meta_raw:
                try:
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                except json.JSONDecodeError:
                    meta = {}
                if isinstance(meta, dict):
                    ip_hash = str(meta.get("ip_hash") or "").strip()
        if ip_hash:
            payload["ip_hash"] = ip_hash
        try:
            storage.insert_event(payload)
            new_rows.append(payload)
            inserted += 1
        except Exception:
            skipped += 1

    sessions_updated = sessions.rebuild_sessions_for_new_events(new_rows)

    if since is None and events:
        _update_sync_cursor_from_batch(events)

    if inserted:
        settings.set_last_sync(storage.utc_now_iso())

    summary = storage.stats_summary()
    if int(summary.get("total_events") or 0) > 0 and int(summary.get("total_sessions") or 0) == 0:
        sessions.rebuild_sessions()
        summary = storage.stats_summary()

    return {
        "since": since_iso,
        "fetched": len(events),
        "inserted": inserted,
        "skipped": skipped,
        "sessions_updated": sessions_updated,
        "backfill": backfill,
        "worker_url": _base_url(),
    }


def worker_stats() -> dict[str, Any]:
    """Status analityki na Workerze (GET /api/analytics/stats)."""
    secret = collect_secret()
    if not secret:
        return {"ok": False, "error": "no secret"}
    url = f"{_base_url()}/api/analytics/stats"
    req = urllib.request.Request(url, headers=_worker_headers(secret), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def purge_worker_d1(*, days: int = 90) -> dict[str, Any]:
    """Usuwa eventy starsze niż N dni z D1 (Worker)."""
    secret = collect_secret()
    if not secret:
        raise WorkerSyncError("Brak ANALYTICS_COLLECT_SECRET w .env")
    url = f"{_base_url()}/api/analytics/purge?days={max(30, int(days))}"
    req = urllib.request.Request(url, headers=_worker_headers(secret), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise WorkerSyncError(f"Worker HTTP {e.code}: {detail[:400]}") from e
    except urllib.error.URLError as e:
        raise WorkerSyncError(f"Brak połączenia z Workerem: {e}") from e
    if not data.get("ok"):
        raise WorkerSyncError(str(data.get("error") or "Purge failed"))
    return data
