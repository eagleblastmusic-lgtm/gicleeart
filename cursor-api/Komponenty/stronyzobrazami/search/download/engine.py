"""Silnik pobierania — direct URL, IIIF (kafelki), scraping strony."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

from ..http import USER_AGENT
from .iiif_engine import download_iiif_to_file, normalize_iiif_service
from .resolvers import resolve_hit, resolve_url, sanitize_filename, scrape_page_for_iiif
from .types import CancelCheck, DownloadProgress, DownloadResult, DownloadSpec, ProgressCallback


def png_option_applies(spec: DownloadSpec | None) -> bool:
    """PNG z IIIF ma sens tylko dla strategii opartych o serwer IIIF (nie direct CDN)."""
    if not spec:
        return False
    return spec.strategy in ("iiif", "page_scrape")


def _fetch_direct(
    url: str,
    dest: Path,
    *,
    headers: dict[str, str],
    timeout: float = 60.0,
    cancel_check: CancelCheck = None,
) -> tuple[int, int]:
    if cancel_check and cancel_check():
        raise RuntimeError("Anulowano.")
    h = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if cancel_check and cancel_check():
            raise RuntimeError("Anulowano.")
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    try:
        from PIL import Image
        from io import BytesIO

        img = Image.open(BytesIO(data))
        return img.width, img.height
    except (ImportError, OSError, ValueError):
        return 0, 0


def _resolve_page_scrape(spec: DownloadSpec, *, cancel_check: CancelCheck = None) -> DownloadSpec:
    if cancel_check and cancel_check():
        raise RuntimeError("Anulowano.")
    service = scrape_page_for_iiif(spec.page_url, cancel_check=cancel_check)
    if not service:
        try:
            from Komponenty.pobierzobraz.iiif_downloader import resolve_from_page_url

            sid, width, height, suggested, _chunk, _q, _f = resolve_from_page_url(spec.page_url, 25)
            name = spec.suggested_filename or suggested or "obraz.jpg"
            return DownloadSpec(
                strategy="iiif",
                source_id=spec.source_id,
                title=spec.title,
                artist=spec.artist,
                service_id=sid,
                suggested_filename=name,
                width=width,
                height=height,
            )
        except Exception as exc:
            raise RuntimeError(f"Nie znaleziono IIIF na stronie: {exc}") from exc
    return DownloadSpec(
        strategy="iiif",
        source_id=spec.source_id,
        title=spec.title,
        artist=spec.artist,
        service_id=service,
        suggested_filename=spec.suggested_filename,
        headers=spec.headers,
        page_url=spec.page_url,
    )


def _dest_path(dest_dir: Path, name: str, *, force_png: bool, strategy: str) -> Path:
    if force_png and strategy in ("iiif", "page_scrape"):
        name = str(Path(name).with_suffix(".png"))
    if not Path(name).suffix:
        name = sanitize_filename(name)
    dest = dest_dir / name
    if dest.exists():
        stem = dest.stem
        ext = dest.suffix
        n = 2
        while dest.exists():
            dest = dest_dir / f"{stem} ({n}){ext}"
            n += 1
    return dest


def download_spec(
    spec: DownloadSpec,
    dest_dir: Path,
    *,
    filename: str = "",
    workers: int = 8,
    force_png: bool = False,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck = None,
) -> DownloadResult:
    if not spec.ok and spec.strategy == "page_scrape":
        try:
            spec = _resolve_page_scrape(spec, cancel_check=cancel_check)
        except RuntimeError as exc:
            return DownloadResult(ok=False, error=str(exc), strategy=spec.strategy)

    if cancel_check and cancel_check():
        return DownloadResult(ok=False, error="Anulowano.", strategy=spec.strategy)

    if not spec.ok:
        return DownloadResult(ok=False, error="Brak danych do pobrania.", strategy=spec.strategy)

    use_png = force_png and png_option_applies(spec)

    name = filename or spec.suggested_filename or "obraz.jpg"
    if not Path(name).suffix:
        name = sanitize_filename(name)
    dest = _dest_path(dest_dir, name, force_png=use_png, strategy=spec.strategy)

    try:
        if spec.strategy == "direct":
            if on_progress:
                on_progress(DownloadProgress(phase="direct", message="Pobieranie pliku…"))
            w, h = _fetch_direct(spec.direct_url, dest, headers=spec.headers, cancel_check=cancel_check)
            return DownloadResult(ok=True, path=str(dest), width=w, height=h, strategy="direct")

        if spec.strategy == "iiif":
            service = normalize_iiif_service(spec.service_id)
            w, h = download_iiif_to_file(
                service,
                dest,
                headers=spec.headers,
                workers=workers,
                force_png=use_png,
                on_progress=on_progress,
                cancel_check=cancel_check,
            )
            return DownloadResult(ok=True, path=str(dest), width=w, height=h, strategy="iiif")

        if spec.strategy == "page_scrape":
            resolved = _resolve_page_scrape(spec, cancel_check=cancel_check)
            return download_spec(
                resolved,
                dest_dir,
                filename=filename,
                workers=workers,
                force_png=force_png,
                on_progress=on_progress,
                cancel_check=cancel_check,
            )

        if spec.strategy == "assetbank_post":
            from ..birmingham_trust_api import download_birmingham_trust_hd

            if on_progress:
                on_progress(DownloadProgress(phase="assetbank", message="Pobieranie JPEG z Asset Bank…"))
            w, h = download_birmingham_trust_hd(
                object_url=spec.page_url,
                dest=dest,
                cancel_check=cancel_check,
            )
            return DownloadResult(ok=True, path=str(dest), width=w, height=h, strategy="assetbank_post")

        return DownloadResult(ok=False, error=f"Nieobsługiwana strategia: {spec.strategy}", strategy=spec.strategy)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, OSError, ValueError) as exc:
        return DownloadResult(ok=False, error=str(exc), strategy=spec.strategy)


def download_hit(
    hit,
    dest_dir: Path,
    *,
    filename: str = "",
    workers: int = 8,
    force_png: bool = False,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck = None,
) -> DownloadResult:
    spec = resolve_hit(hit)
    if not spec or not spec.ok:
        if spec and spec.strategy == "page_scrape":
            return download_spec(
                spec,
                dest_dir,
                filename=filename,
                workers=workers,
                force_png=force_png,
                on_progress=on_progress,
                cancel_check=cancel_check,
            )
        return DownloadResult(ok=False, error="Nie udalo sie ustalic sposobu pobrania dla tego wyniku.")
    return download_spec(
        spec,
        dest_dir,
        filename=filename,
        workers=workers,
        force_png=force_png,
        on_progress=on_progress,
        cancel_check=cancel_check,
    )


def download_link(
    url: str,
    dest_dir: Path,
    *,
    filename: str = "",
    workers: int = 8,
    force_png: bool = False,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck = None,
) -> DownloadResult:
    spec = resolve_url(url)
    if not spec:
        return DownloadResult(ok=False, error="Pusty adres URL.")
    return download_spec(
        spec,
        dest_dir,
        filename=filename,
        workers=workers,
        force_png=force_png,
        on_progress=on_progress,
        cancel_check=cancel_check,
    )
