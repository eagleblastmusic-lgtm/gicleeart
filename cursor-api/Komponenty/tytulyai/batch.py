"""Batch: produkt Shopify -> Gemini -> prompt do Cursora."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from Komponenty._shared.clipboard_image import fetch_image_bytes, shopify_sized_image_url
from Komponenty._shared.gemini_client import (
    GeminiAborted,
    format_gemini_error,
    generate_from_image_bytes,
    generate_from_image_file,
    image_mime_type,
)
from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.dodajobraz.description_update import build_title_change_prompt

from .catalog_context import collision_warning, other_pl_titles_for_artist
from .parse_response import parse_gemini_title_fields
from .prompts import build_generation_prompt

IMAGE_MAX_WIDTH = 1600


@dataclass
class BatchItemResult:
    product_id: int
    artist: str
    painting_title: str
    model_used: str
    raw_response: str
    cursor_prompt: str
    error: str = ""
    warning: str = ""
    generated_at: str = ""


@dataclass
class PrefetchedImage:
    row_key: int
    image_bytes: bytes | None = None
    mime_type: str = "image/jpeg"
    error: str = ""


def resolve_product_image_url(row: dict) -> str:
    image_url = (row.get("image_src") or "").strip()
    if image_url:
        return image_url
    pid = int(row.get("product_id") or 0)
    if not pid:
        return ""
    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, pid)
    img = prod.get("image") or {}
    image_url = (img.get("src") or "").strip()
    if image_url:
        return image_url
    for im in prod.get("images") or []:
        src = (im.get("src") or "").strip()
        if src:
            return src
    return ""


def _mime_from_url(url: str) -> str:
    tail = url.rsplit("/", 1)[-1].split("?", 1)[0].lower()
    return image_mime_type(Path(tail))


def fetch_image_bytes_for_row(row: dict, *, width: int = IMAGE_MAX_WIDTH) -> tuple[bytes, str]:
    url = resolve_product_image_url(row)
    if not url:
        raise ValueError("Brak grafiki glownej produktu.")
    sized = shopify_sized_image_url(url, width=width)
    return fetch_image_bytes(sized), _mime_from_url(url)


def prefetch_row_images(
    rows: list[dict],
    *,
    width: int | None = None,
    max_workers: int = 8,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[int, PrefetchedImage]:
    """Rownolegle pobiera miniatury przed wywolaniami Gemini."""
    out: dict[int, PrefetchedImage] = {}
    if not rows:
        return out

    def _one(row: dict) -> PrefetchedImage:
        key = id(row)
        try:
            data, mime = fetch_image_bytes_for_row(
                row, width=width if width is not None else IMAGE_MAX_WIDTH,
            )
            return PrefetchedImage(row_key=key, image_bytes=data, mime_type=mime)
        except Exception as exc:
            return PrefetchedImage(row_key=key, error=str(exc))

    workers = max(1, min(max_workers, len(rows)))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, row): row for row in rows}
        for fut in as_completed(futures):
            item = fut.result()
            out[item.row_key] = item
            done += 1
            if on_progress:
                on_progress(done, len(rows))
    return out


def process_product_row(
    row: dict,
    *,
    model: str,
    api_key: str | None = None,
    local_image: Path | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    catalog_rows: list[dict] | None = None,
    on_status: Callable[[str], None] | None = None,
    should_abort: Callable[[], bool] | None = None,
) -> BatchItemResult:
    pid = int(row.get("product_id") or 0)
    artist = str(row.get("artist") or "").strip()
    painting_title = str(row.get("painting_title") or "").strip()
    base = BatchItemResult(
        product_id=pid,
        artist=artist,
        painting_title=painting_title,
        model_used="",
        raw_response="",
        cursor_prompt="",
    )
    if not artist:
        base.error = "Brak artysty w danych produktu."
        return base

    prompt = build_generation_prompt(
        artist=artist,
        painting_title=painting_title,
        other_pl_titles_same_artist=other_pl_titles_for_artist(
            catalog_rows or [row],
            artist=artist,
            exclude_product_id=pid,
        ),
    )

    try:
        gen_kw = {
            "prompt": prompt,
            "api_key": api_key,
            "model": model,
            "on_status": on_status,
            "should_abort": should_abort,
        }
        if local_image and local_image.is_file():
            raw, used_model = generate_from_image_file(
                image_path=local_image,
                **gen_kw,
            )
        elif image_bytes:
            raw, used_model = generate_from_image_bytes(
                image_bytes=image_bytes,
                mime_type=mime_type,
                **gen_kw,
            )
        else:
            if on_status:
                on_status("Pobieram miniature produktu...")
            data, mime = fetch_image_bytes_for_row(row)
            raw, used_model = generate_from_image_bytes(
                image_bytes=data,
                mime_type=mime,
                **gen_kw,
            )
    except GeminiAborted:
        raise
    except Exception as exc:
        base.error = format_gemini_error(exc)
        return base

    try:
        fields = parse_gemini_title_fields(raw)
        cursor_prompt = build_title_change_prompt(
            painting_title=painting_title,
            artist=artist,
            titles=fields,
        )
        warn = collision_warning(
            fields.get("pl") or painting_title,
            artist=artist,
            product_id=pid,
            catalog_rows=catalog_rows or [row],
        )
        if warn:
            base.warning = warn
            cursor_prompt = f"<!-- UWAGA: {warn} -->\n\n{cursor_prompt}"
    except ValueError as exc:
        base.model_used = used_model
        base.raw_response = raw
        base.error = f"Nie udalo sie sparsowac odpowiedzi: {exc}"
        return base

    base.model_used = used_model
    base.raw_response = raw
    base.cursor_prompt = cursor_prompt
    base.generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return base


def process_image_file(
    path: Path,
    *,
    artist: str,
    painting_title: str,
    model: str,
    api_key: str | None = None,
) -> BatchItemResult:
    row = {
        "product_id": 0,
        "artist": artist,
        "painting_title": painting_title,
    }
    return process_product_row(
        row,
        model=model,
        api_key=api_key,
        local_image=path,
    )
