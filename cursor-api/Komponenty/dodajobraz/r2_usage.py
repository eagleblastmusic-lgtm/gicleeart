"""Zużycie R2: magazyn w buckecie (S3 API) i opcjonalnie metryki konta (Cloudflare API)."""

from __future__ import annotations

import json
import os
import ssl
import statistics
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .r2_storage import R2Config, _load_dotenv_into_environ, _s3_client, load_r2_config

DEFAULT_STORAGE_QUOTA_GB = 10.0
DEFAULT_CLASS_A_QUOTA = 1_000_000
DEFAULT_CLASS_B_QUOTA = 10_000_000
DEFAULT_ZOOM_ESTIMATE_BYTES = 450 * 1024 * 1024
ZOOM_HISTORY_MAX = 40
ZOOM_HISTORY_RECENT = 8
ZOOM_BUCKET_RECENT = 8


@dataclass(frozen=True)
class R2UsageSnapshot:
    bucket: str
    storage_bytes: int
    object_count: int
    zoom_bytes: int
    zoom_object_count: int
    storage_quota_bytes: int
    class_a_used: int | None
    class_a_quota: int
    class_b_used: int | None
    class_b_quota: int
    source: str
    note: str
    zoom_work_count: int = 0
    zoom_estimate_count: int | None = None
    zoom_estimate_avg_bytes: int | None = None
    zoom_estimate_sample_n: int = 0
    zoom_estimate_source: str = ""
    error: str | None = None


def _quota_bytes() -> int:
    _load_dotenv_into_environ()
    raw = (os.environ.get("R2_STORAGE_QUOTA_GB") or "").strip()
    try:
        gb = float(raw) if raw else DEFAULT_STORAGE_QUOTA_GB
    except ValueError:
        gb = DEFAULT_STORAGE_QUOTA_GB
    if gb <= 0:
        gb = DEFAULT_STORAGE_QUOTA_GB
    return int(gb * 1024**3)


def _int_env(name: str, default: int) -> int:
    _load_dotenv_into_environ()
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw.replace("_", "")))
    except ValueError:
        return default


def _fmt_int(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")


def format_bytes(n: int) -> str:
    """Czytelny rozmiar (GB z przecinkiem dla PL)."""
    n = max(0, int(n))
    if n >= 1024**3:
        gb = n / (1024**3)
        return f"{gb:.2f} GB".replace(".", ",")
    if n >= 1024**2:
        mb = n / (1024**2)
        return f"{mb:.1f} MB".replace(".", ",")
    if n >= 1024:
        return f"{n // 1024} KB"
    return f"{n} B"


def _zoom_history_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "zoom_upload_history.json"


def _default_zoom_estimate_bytes() -> int:
    _load_dotenv_into_environ()
    raw = (os.environ.get("R2_ZOOM_ESTIMATE_MB") or "").strip()
    if raw:
        try:
            mb = float(raw.replace(",", "."))
            if mb > 0:
                return int(mb * 1024 * 1024)
        except ValueError:
            pass
    return DEFAULT_ZOOM_ESTIMATE_BYTES


def record_zoom_upload(*, total_bytes: int, handle: str) -> None:
    """Zapisuje rozmiar ostatniego uploadu zoom (do szacunku w GUI)."""
    if total_bytes <= 0:
        return
    path = _zoom_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if path.is_file():
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                rows = []
        except (json.JSONDecodeError, OSError):
            rows = []
    rows.append(
        {
            "bytes": int(total_bytes),
            "handle": (handle or "").strip(),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    rows = rows[-ZOOM_HISTORY_MAX:]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")


def _load_recent_upload_byte_sizes(max_entries: int = ZOOM_HISTORY_RECENT) -> list[int]:
    path = _zoom_history_path()
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(rows, list):
        return []
    out: list[int] = []
    for row in reversed(rows):
        if not isinstance(row, dict):
            continue
        b = int(row.get("bytes") or 0)
        if b > 0:
            out.append(b)
        if len(out) >= max_entries:
            break
    return list(reversed(out))


def zoom_work_sizes_from_bucket(cfg: R2Config) -> list[tuple[str, int, datetime]]:
    """Suma bajtow na dzielo (zoom/<handle>/...) + czas ostatniego pliku."""
    client = _s3_client(cfg)
    by_work: dict[str, list[tuple[int, datetime]]] = {}
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cfg.bucket, Prefix="zoom/"):
        for obj in page.get("Contents") or []:
            key = obj.get("Key") or ""
            parts = key.split("/")
            if len(parts) < 3 or parts[0] != "zoom":
                continue
            work = parts[1]
            size = int(obj.get("Size") or 0)
            lm = obj.get("LastModified")
            if lm is None:
                lm_dt = datetime.min.replace(tzinfo=timezone.utc)
            elif isinstance(lm, datetime):
                lm_dt = lm if lm.tzinfo else lm.replace(tzinfo=timezone.utc)
            else:
                lm_dt = datetime.min.replace(tzinfo=timezone.utc)
            by_work.setdefault(work, []).append((size, lm_dt))
    result: list[tuple[str, int, datetime]] = []
    for work, items in by_work.items():
        total = sum(s for s, _ in items)
        latest = max(lm for _, lm in items)
        result.append((work, total, latest))
    result.sort(key=lambda x: x[2], reverse=True)
    return result


def estimate_zooms_remaining(
    free_bytes: int,
    *,
    bucket_work_sizes: list[int],
    local_recent_sizes: list[int],
) -> tuple[int | None, int | None, int, str]:
    """Zwraca (szac. liczba zoomow, sredni rozmiar B, probka N, opis zrodla)."""
    free_bytes = max(0, int(free_bytes))
    default_b = _default_zoom_estimate_bytes()
    sizes: list[int] = []
    source = ""

    if len(local_recent_sizes) >= 2:
        sizes = local_recent_sizes[-ZOOM_HISTORY_RECENT:]
        source = "ostatnie uploady w aplikacji"
    elif bucket_work_sizes:
        recent = bucket_work_sizes[:ZOOM_BUCKET_RECENT]
        sizes = recent
        source = f"{len(recent)} dziel w R2"
    else:
        sizes = [default_b]
        source = "domyslne ~450 MB (brak historii)"

    avg = int(statistics.median(sizes))
    if avg <= 0:
        avg = default_b
    count = free_bytes // avg if free_bytes else 0
    return count, avg, len(sizes), source


def sum_bucket_storage(cfg: R2Config, *, prefix_filter: str = "zoom/") -> tuple[int, int, int, int]:
    """Zwraca (storage_bytes, object_count, zoom_bytes, zoom_object_count)."""
    client = _s3_client(cfg)
    total_b = 0
    total_n = 0
    zoom_b = 0
    zoom_n = 0
    pfx = prefix_filter.strip("/")
    if pfx:
        pfx = pfx + "/"
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cfg.bucket):
        for obj in page.get("Contents") or []:
            key = obj.get("Key") or ""
            size = int(obj.get("Size") or 0)
            total_b += size
            total_n += 1
            if pfx and key.startswith(pfx):
                zoom_b += size
                zoom_n += 1
    return total_b, total_n, zoom_b, zoom_n


def _cf_api_token() -> str:
    _load_dotenv_into_environ()
    return (
        (os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN") or "")
        .strip()
    )


def _cf_get_json(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cf_post_graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sum_payload_from_r2_metrics(result: dict[str, Any]) -> int:
    """Suma payload+metadata ze standard published+uploaded (bajty)."""
    total = 0
    std = result.get("standard") or {}
    for state in ("published", "uploaded"):
        block = std.get(state) or {}
        total += int(block.get("payloadSize") or 0)
        total += int(block.get("metadataSize") or 0)
    return total


def fetch_account_storage_api(account_id: str, token: str) -> int | None:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/metrics"
    data = _cf_get_json(url, token)
    if not data.get("success"):
        return None
    return _sum_payload_from_r2_metrics(data.get("result") or {})


def fetch_monthly_operations(
    account_id: str,
    token: str,
    bucket_name: str,
) -> tuple[int | None, int | None]:
    """Class A (zapisy/listy) vs Class B (odczyty) w biezacym miesiacu — przyblizenie z GraphQL."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query = """
    query R2Ops($accountTag: string!, $start: Time, $end: Time, $bucket: string) {
      viewer {
        accounts(filter: { accountTag: $accountTag }) {
          r2OperationsAdaptiveGroups(
            limit: 10000
            filter: {
              datetime_geq: $start
              datetime_leq: $end
              bucketName: $bucket
            }
          ) {
            sum { requests }
            dimensions { actionType }
          }
        }
      }
    }
    """
    variables = {
        "accountTag": account_id,
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket": bucket_name,
    }
    data = _cf_post_graphql(token, query, variables)
    if data.get("errors"):
        return None, None
    accounts = (data.get("data") or {}).get("viewer", {}).get("accounts") or []
    if not accounts:
        return None, None
    groups = accounts[0].get("r2OperationsAdaptiveGroups") or []
    class_a = 0
    class_b = 0
    a_ops = {
        "PutObject",
        "CopyObject",
        "CompleteMultipartUpload",
        "CreateMultipartUpload",
        "UploadPart",
        "ListBuckets",
        "ListObjects",
        "ListObjectsV2",
        "DeleteObject",
        "DeleteObjects",
    }
    for g in groups:
        action = (g.get("dimensions") or {}).get("actionType") or ""
        reqs = int((g.get("sum") or {}).get("requests") or 0)
        if action in a_ops:
            class_a += reqs
        else:
            class_b += reqs
    return class_a, class_b


def collect_r2_usage() -> R2UsageSnapshot:
    """Zbiera stan zużycia; przy braku R2 rzuca RuntimeError jak load_r2_config."""
    cfg = load_r2_config()
    quota_b = _quota_bytes()
    class_a_q = _int_env("R2_CLASS_A_QUOTA", DEFAULT_CLASS_A_QUOTA)
    class_b_q = _int_env("R2_CLASS_B_QUOTA", DEFAULT_CLASS_B_QUOTA)
    err_parts: list[str] = []
    try:
        storage_b, obj_n, zoom_b, zoom_n = sum_bucket_storage(cfg)
        work_rows = zoom_work_sizes_from_bucket(cfg)
        source = "bucket"
    except Exception as e:
        raise RuntimeError(f"Nie mozna odczytac bucketu R2: {e}") from e

    free_b = max(0, quota_b - storage_b)
    local_sizes = _load_recent_upload_byte_sizes()
    est_count, est_avg, est_n, est_src = estimate_zooms_remaining(
        free_b,
        bucket_work_sizes=[b for _, b, _ in work_rows],
        local_recent_sizes=local_sizes,
    )

    token = _cf_api_token()
    class_a: int | None = None
    class_b: int | None = None
    note = (
        "Egress (transfer do internetu z R2/r2.dev) jest u Cloudflare bezplatny — "
        "limituje glownie magazyn w buckecie."
    )
    if token:
        try:
            api_b = fetch_account_storage_api(cfg.account_id, token)
            if api_b is not None and api_b > storage_b:
                storage_b = api_b
                source = "bucket+api"
        except Exception as e:
            err_parts.append(f"metryki konta: {e}")
        try:
            class_a, class_b = fetch_monthly_operations(cfg.account_id, token, cfg.bucket)
        except Exception as e:
            err_parts.append(f"operacje: {e}")
    else:
        note += " Opcjonalnie: CLOUDFLARE_API_TOKEN w .env — operacje Class A/B w tym miesiacu."

    return R2UsageSnapshot(
        bucket=cfg.bucket,
        storage_bytes=storage_b,
        object_count=obj_n,
        zoom_bytes=zoom_b,
        zoom_object_count=zoom_n,
        storage_quota_bytes=quota_b,
        class_a_used=class_a,
        class_a_quota=class_a_q,
        class_b_used=class_b,
        class_b_quota=class_b_q,
        source=source,
        note=note,
        zoom_work_count=len(work_rows),
        zoom_estimate_count=est_count,
        zoom_estimate_avg_bytes=est_avg,
        zoom_estimate_sample_n=est_n,
        zoom_estimate_source=est_src,
        error="; ".join(err_parts) if err_parts else None,
    )


def format_usage_line(snap: R2UsageSnapshot) -> str:
    free_b = max(0, snap.storage_quota_bytes - snap.storage_bytes)
    line = (
        f"R2 {snap.bucket}: {format_bytes(snap.storage_bytes)} / "
        f"{format_bytes(snap.storage_quota_bytes)} "
        f"(wolne {format_bytes(free_b)}, {snap.object_count} plikow"
    )
    if snap.zoom_object_count:
        line += f", zoom {format_bytes(snap.zoom_bytes)}"
    line += ")"
    if snap.zoom_estimate_count is not None and snap.zoom_estimate_avg_bytes:
        line += (
            f" | ~{_fmt_int(snap.zoom_estimate_count)} kolejnych zoomow"
            f" (ok. {format_bytes(snap.zoom_estimate_avg_bytes)}/dzielo"
        )
        if snap.zoom_estimate_sample_n:
            line += f", {snap.zoom_estimate_source}"
        line += ")"
    if snap.class_a_used is not None:
        a_free = max(0, snap.class_a_quota - snap.class_a_used)
        b_free = max(0, snap.class_b_quota - (snap.class_b_used or 0))
        line += (
            f" | oper. A: {_fmt_int(snap.class_a_used)}/{_fmt_int(snap.class_a_quota)}"
            f" (wolne {_fmt_int(a_free)})"
        )
        if snap.class_b_used is not None:
            line += (
                f", B: {_fmt_int(snap.class_b_used)}/{_fmt_int(snap.class_b_quota)}"
                f" (wolne {_fmt_int(b_free)})"
            )
    line += " | egress: bez limitu (CF)"
    if snap.error:
        line += f" | uwaga: {snap.error}"
    return line


def usage_percent(used: int, quota: int) -> float:
    if quota <= 0:
        return 0.0
    return min(100.0, (max(0, used) / quota) * 100.0)


def usage_status(pct: float) -> tuple[str, str]:
    """Zwraca (etykieta, kolor hex) dla progu zużycia."""
    if pct >= 100.0:
        return "PRZEKROCZONY", "#c62828"
    if pct >= 90.0:
        return "Krytycznie", "#e65100"
    if pct >= 75.0:
        return "Uwaga", "#f57f17"
    return "OK", "#2e7d32"


def sum_prefix_bytes(cfg: R2Config, prefix: str) -> tuple[int, int]:
    """Suma bajtow i liczba obiektow pod prefixem (np. customer-uploads/)."""
    client = _s3_client(cfg)
    pfx = prefix.strip("/") + "/"
    total_b = 0
    total_n = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cfg.bucket, Prefix=pfx):
        for obj in page.get("Contents") or []:
            total_b += int(obj.get("Size") or 0)
            total_n += 1
    return total_b, total_n


def enrich_snapshot_with_uploads(snap: R2UsageSnapshot) -> dict[str, Any]:
    """Dodatkowy podzial bucketu (customer-uploads vs zoom) do okna Cloudflare."""
    cfg = load_r2_config()
    try:
        uploads_b, uploads_n = sum_prefix_bytes(cfg, "customer-uploads")
    except Exception:
        uploads_b, uploads_n = 0, 0
    other_b = max(0, snap.storage_bytes - snap.zoom_bytes - uploads_b)
    return {
        "customer_uploads_bytes": uploads_b,
        "customer_uploads_count": uploads_n,
        "other_bytes": other_b,
    }
