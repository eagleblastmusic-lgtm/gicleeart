"""IIIF — parsowanie URL, info.json, pobieranie pelnej rozdzielczosci (kafelki)."""

from __future__ import annotations

import json
import math
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from ..http import USER_AGENT, get_json
from .cache import cached
from .types import CancelCheck, DownloadProgress, ProgressCallback

_CHECKPOINT_EVERY = 25

_IIIF_FULL_RE = re.compile(
    r"^(?P<base>https?://[^/]+(?:/[^/]+)*)/full/[^/]+/[^/]+/[^/]+\.(?:jpg|jpeg|png|webp|tif|tiff)$",
    re.IGNORECASE,
)
_IIIF_THUMB_SUFFIX_RE = re.compile(r"__small$", re.IGNORECASE)


def iiif_service_from_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.endswith("/info.json"):
        return u[: -len("/info.json")]
    m = _IIIF_FULL_RE.match(u)
    if m:
        return m.group("base")
    if "/full/" in u:
        return u.split("/full/", 1)[0]
    if "/info.json" in u:
        return u.split("/info.json", 1)[0]
    return u


def normalize_iiif_service(service_id: str) -> str:
    sid = (service_id or "").strip()
    sid = _IIIF_THUMB_SUFFIX_RE.sub("", sid)
    marker = ".tif"
    pos = sid.lower().find(marker)
    if pos != -1:
        return sid[: pos + len(marker)]
    return sid


def fetch_iiif_info(service_id: str, *, timeout: float = 25.0, headers: dict[str, str] | None = None) -> dict:
    base = normalize_iiif_service(service_id)
    cache_key = f"iiifinfo:{base}"
    return cached(
        cache_key,
        lambda: _fetch_iiif_info_uncached(base, timeout=timeout, headers=headers),
        ttl=900.0,
    )


def _fetch_iiif_info_uncached(
    base: str,
    *,
    timeout: float,
    headers: dict[str, str] | None,
) -> dict:
    info_url = base if base.endswith("/info.json") else f"{base}/info.json"
    data = get_json(info_url, timeout=timeout, headers=headers)
    if not isinstance(data, dict):
        raise RuntimeError("Niepoprawny info.json IIIF.")
    sid = data.get("id") or data.get("@id") or base
    width = int(data.get("width") or 0)
    height = int(data.get("height") or 0)
    if not sid or width <= 0 or height <= 0:
        raise RuntimeError("Brak wymiarow w info.json IIIF.")
    tiles = data.get("tiles") or []
    tile_w = 256
    if tiles and isinstance(tiles[0], dict):
        tile_w = int(tiles[0].get("width") or tile_w)
    max_w = data.get("maxWidth") or tile_w
    chunk = min(int(max_w), tile_w, width, height, 1024)
    chunk = max(256, chunk)
    return {
        "service_id": str(sid).rstrip("/"),
        "width": width,
        "height": height,
        "tile": chunk,
    }


def _request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    if extra:
        h.update(extra)
    return h


def _fetch_bytes(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    retries: int = 3,
) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            req = urllib.request.Request(url, headers=_request_headers(headers))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt + 1 >= retries:
                break
            time.sleep(min(2.0 ** attempt, 4.0))
    if last_exc:
        raise last_exc
    raise RuntimeError("Nie udalo sie pobrac danych.")


_THREAD_LOCAL = threading.local()


def _get_session_headers(headers: dict[str, str]) -> dict[str, str]:
    return _request_headers(headers)


def _try_single_full(
    service_id: str,
    *,
    timeout: float,
    headers: dict[str, str] | None,
    force_png: bool = False,
) -> tuple[bytes, int, int] | None:
    base = normalize_iiif_service(service_id)
    formats = ("png", "jpg", "webp", "tif") if force_png else ("jpg", "png", "tif", "webp")
    for region in ("max", "full"):
        for quality in ("default", "native", "color"):
            for fmt in formats:
                url = f"{base}/full/{region}/0/{quality}.{fmt}"
                try:
                    raw = _fetch_bytes(url, timeout=timeout, headers=headers)
                    if len(raw) < 512:
                        continue
                    from PIL import Image

                    img = Image.open(BytesIO(raw))
                    return raw, img.width, img.height
                except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError):
                    continue
    return None


def _tile_jobs(width: int, height: int, tile: int):
    cols = math.ceil(width / tile)
    rows = math.ceil(height / tile)
    for row in range(rows):
        for col in range(cols):
            x = col * tile
            y = row * tile
            w = min(tile, width - x)
            h = min(tile, height - y)
            yield row, col, x, y, w, h


def _fetch_tile(
    service_id: str,
    job: tuple[int, int, int, int, int, int],
    *,
    timeout: float,
    headers: dict[str, str] | None,
) -> tuple[int, int, int, int, bytes]:
    _row, _col, x, y, w, h = job
    base = normalize_iiif_service(service_id)
    url = f"{base}/{x},{y},{w},{h}/{w},{h}/0/default.jpg"
    raw = _fetch_bytes(url, timeout=timeout, headers=headers)
    return x, y, w, h, raw


def _checkpoint_paths(dest: Path) -> tuple[Path, Path]:
    partial = dest.with_name(f"{dest.stem}.partial{dest.suffix or '.jpg'}")
    state = dest.with_name(f"{dest.stem}.iiifstate.json")
    return partial, state


def _load_tile_checkpoint(
    dest: Path,
    *,
    width: int,
    height: int,
    tile: int,
) -> tuple[set[str], object | None]:
    partial, state = _checkpoint_paths(dest)
    if not partial.is_file() or not state.is_file():
        return set(), None
    try:
        from PIL import Image

        data = json.loads(state.read_text(encoding="utf-8"))
        if int(data.get("width") or 0) != width or int(data.get("height") or 0) != height:
            return set(), None
        if int(data.get("tile") or 0) != tile:
            return set(), None
        done = {str(x) for x in (data.get("done_tiles") or [])}
        canvas = Image.open(partial).convert("RGB")
        if canvas.width != width or canvas.height != height:
            return set(), None
        return done, canvas
    except (OSError, ValueError, json.JSONDecodeError):
        return set(), None


def _save_tile_checkpoint(
    dest: Path,
    canvas,
    *,
    width: int,
    height: int,
    tile: int,
    done_tiles: set[str],
) -> None:
    partial, state = _checkpoint_paths(dest)
    partial.parent.mkdir(parents=True, exist_ok=True)
    ext = dest.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        canvas.save(partial, format="JPEG", quality=92)
    elif ext == ".png":
        canvas.save(partial, format="PNG")
    else:
        canvas.save(partial, format="JPEG", quality=92)
    state.write_text(
        json.dumps(
            {
                "width": width,
                "height": height,
                "tile": tile,
                "done_tiles": sorted(done_tiles),
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )


def _tile_key(job: tuple[int, int, int, int, int, int]) -> str:
    row, col, _x, _y, _w, _h = job
    return f"{row}:{col}"


def download_iiif_to_file(
    service_id: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    workers: int = 8,
    timeout: float = 30.0,
    force_png: bool = False,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck = None,
) -> tuple[int, int]:
    info = fetch_iiif_info(service_id, timeout=timeout, headers=headers)
    sid = info["service_id"]
    width = info["width"]
    height = info["height"]
    tile = info["tile"]

    if on_progress:
        fmt_hint = "PNG" if force_png else "JPEG"
        on_progress(DownloadProgress(phase="probe", message=f"IIIF {width}×{height}px ({fmt_hint})"))

    single = _try_single_full(sid, timeout=timeout, headers=headers, force_png=force_png)
    if single is not None:
        raw, w, h = single
        dest.parent.mkdir(parents=True, exist_ok=True)
        if force_png and dest.suffix.lower() not in (".png",):
            dest = dest.with_suffix(".png")
        dest.write_bytes(raw)
        if on_progress:
            on_progress(DownloadProgress(phase="done", done=1, total=1, message="Pobrano jednym zapytaniem."))
        return w, h

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Brak biblioteki Pillow (PIL) do skladania kafelkow IIIF.") from exc

    jobs = list(_tile_jobs(width, height, tile))
    total = len(jobs)
    done_tiles, canvas_loaded = _load_tile_checkpoint(dest, width=width, height=height, tile=tile)
    if canvas_loaded is not None:
        canvas = canvas_loaded
    else:
        canvas = Image.new("RGB", (width, height))
        done_tiles = set()

    pending_jobs = [job for job in jobs if _tile_key(job) not in done_tiles]
    done = len(jobs) - len(pending_jobs)

    if on_progress:
        on_progress(
            DownloadProgress(
                phase="tiles",
                done=done,
                total=total,
                message=f"Kafelki IIIF ({tile}px)" + (" — wznowiono" if done else ""),
            ),
        )

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_fetch_tile, sid, job, timeout=timeout, headers=headers): job
            for job in pending_jobs
        }
        for future in as_completed(futures):
            if cancel_check and cancel_check():
                _save_tile_checkpoint(
                    dest,
                    canvas,
                    width=width,
                    height=height,
                    tile=tile,
                    done_tiles=done_tiles,
                )
                raise RuntimeError("Anulowano.")
            job = futures[future]
            x, y, w, h, raw = future.result()
            tile_img = Image.open(BytesIO(raw)).convert("RGB")
            canvas.paste(tile_img, (x, y))
            done_tiles.add(_tile_key(job))
            done += 1
            if on_progress:
                on_progress(DownloadProgress(phase="tiles", done=done, total=total))
            if done % _CHECKPOINT_EVERY == 0 or done == total:
                _save_tile_checkpoint(
                    dest,
                    canvas,
                    width=width,
                    height=height,
                    tile=tile,
                    done_tiles=done_tiles,
                )

    dest.parent.mkdir(parents=True, exist_ok=True)
    if force_png:
        dest = dest.with_suffix(".png")
    ext = dest.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        canvas.save(dest, format="JPEG", quality=95)
    elif ext == ".png":
        canvas.save(dest, format="PNG")
    else:
        canvas.save(dest, format="JPEG", quality=95)
    partial, state = _checkpoint_paths(dest)
    for path in (partial, state):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return width, height
