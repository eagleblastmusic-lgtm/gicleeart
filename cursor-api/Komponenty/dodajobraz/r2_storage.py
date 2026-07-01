"""Upload plikow do Cloudflare R2 (S3-compatible API)."""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote

Logger = Callable[[str], None]

try:
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    _HAS_BOTO = True
except ImportError:
    _HAS_BOTO = False


@dataclass(frozen=True)
class R2Config:
    account_id: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    endpoint: str
    public_base_url: str


def _load_dotenv_into_environ() -> None:
    try:
        from Komponenty.nazwijobraz.env_loader import load_env

        load_env()
    except Exception:
        pass


def load_r2_config() -> R2Config:
    _load_dotenv_into_environ()
    missing = []
    keys = {
        "account_id": "R2_ACCOUNT_ID",
        "bucket": "R2_BUCKET",
        "access_key_id": "R2_ACCESS_KEY_ID",
        "secret_access_key": "R2_SECRET_ACCESS_KEY",
        "endpoint": "R2_ENDPOINT",
        "public_base_url": "R2_PUBLIC_BASE_URL",
    }
    vals: dict[str, str] = {}
    for field, env_key in keys.items():
        v = (os.environ.get(env_key) or "").strip()
        if not v:
            missing.append(env_key)
        vals[field] = v
    if missing:
        raise RuntimeError(
            "Brak konfiguracji R2 w cursor-api/.env: " + ", ".join(missing)
        )
    return R2Config(**vals)  # type: ignore[arg-type]


def _int_env(name: str, default: int, *, lo: int = 1, hi: int = 64) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        n = int(raw)
    except ValueError:
        return default
    return max(lo, min(hi, n))


def upload_workers_default() -> int:
    """Rownolegle PUT-y w ramach jednego zoomu (kafelki). Env: R2_UPLOAD_WORKERS."""
    return _int_env("R2_UPLOAD_WORKERS", 12)


def zoom_parallel_products_default() -> int:
    """Ile zoomow (produktow) jednoczesnie przy batchu. Env: R2_ZOOM_PARALLEL."""
    return _int_env("R2_ZOOM_PARALLEL", 3, hi=8)


def _s3_client(cfg: R2Config, *, max_pool_connections: int = 12):
    if not _HAS_BOTO:
        raise RuntimeError("Brak boto3 — zainstaluj: pip install boto3")
    pool = max(10, int(max_pool_connections))
    return boto3.client(
        "s3",
        endpoint_url=cfg.endpoint.rstrip("/"),
        aws_access_key_id=cfg.access_key_id,
        aws_secret_access_key=cfg.secret_access_key,
        config=Config(signature_version="s3v4", max_pool_connections=pool),
        region_name="auto",
    )


def _upload_with_client(
    client: object,
    cfg: R2Config,
    *,
    key: str,
    local_path: Path,
    logger: Logger | None = None,
) -> str:
    key = key.lstrip("/")
    ctype, _ = mimetypes.guess_type(local_path.name)
    extra = {"ContentType": ctype or "application/octet-stream"}
    client.upload_file(str(local_path), cfg.bucket, key, ExtraArgs=extra)  # type: ignore[union-attr]
    url = f"{cfg.public_base_url.rstrip('/')}/{quote(key, safe='/')}"
    if logger:
        logger(f"[r2] OK {key}")
    return url


def upload_file(
    cfg: R2Config,
    *,
    key: str,
    local_path: Path,
    logger: Logger | None = None,
) -> str:
    """Wgrywa plik; zwraca publiczny URL (R2 dev / custom domain)."""
    client = _s3_client(cfg)
    return _upload_with_client(client, cfg, key=key, local_path=local_path, logger=logger)


def upload_many(
    cfg: R2Config,
    *,
    prefix: str,
    items: list[tuple[str, Path]],
    logger: Logger | None = None,
    max_workers: int | None = None,
) -> None:
    prefix = prefix.strip("/")
    workers = max_workers if max_workers is not None else upload_workers_default()
    workers = max(1, min(workers, len(items) or 1))

    client = _s3_client(cfg, max_pool_connections=workers + 4)

    if len(items) <= 1 or workers <= 1:
        for rel, path in items:
            key = f"{prefix}/{rel}" if prefix else rel
            _upload_with_client(client, cfg, key=key, local_path=path, logger=logger)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _one(rel: str, path: Path) -> None:
        key = f"{prefix}/{rel}" if prefix else rel
        _upload_with_client(client, cfg, key=key, local_path=path, logger=logger)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, rel, path) for rel, path in items]
        for fut in as_completed(futures):
            fut.result()
