"""Batch roboczych opisow obrazow przez Gemini API (v1 + v2)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from Komponenty._shared.gemini_client import (
    GeminiAborted,
    format_gemini_error,
    generate_from_image_bytes,
)
from Komponenty.dodajobraz.description_update import parse_full_akapity_json
from Komponenty.dodajobraz.prompt_builder import (
    build_image_description_prompt,
    build_image_description_prompt_v2,
)

from .batch import fetch_image_bytes_for_row, prefetch_row_images

DescriptionVariantKey = Literal["v1", "v2"]

VARIANT_LABELS: dict[DescriptionVariantKey, str] = {
    "v1": "Opis z obrazu",
    "v2": "Opis z obrazu v2",
}


@dataclass
class DescriptionVariant:
    model_used: str = ""
    akapity: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: str = ""
    generated_at: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.akapity) and not self.error


@dataclass
class ProductDescriptionDrafts:
    product_id: int
    artist: str
    painting_title: str
    v1: DescriptionVariant = field(default_factory=DescriptionVariant)
    v2: DescriptionVariant = field(default_factory=DescriptionVariant)

    @property
    def ok(self) -> bool:
        return self.v1.ok or self.v2.ok

    def variant(self, key: DescriptionVariantKey) -> DescriptionVariant:
        return self.v1 if key == "v1" else self.v2


def variant_needs_regeneration(variant: DescriptionVariant) -> bool:
    """True gdy wariant nie ma poprawnych akapitow (pusty lub blad generowania)."""
    return not variant.ok


def merge_description_drafts(
    existing: ProductDescriptionDrafts,
    new: ProductDescriptionDrafts,
) -> ProductDescriptionDrafts:
    """Zachowuje udane warianty z poprzedniej sesji; nadpisuje tylko te z bledem."""
    merged = ProductDescriptionDrafts(
        product_id=new.product_id or existing.product_id,
        artist=new.artist or existing.artist,
        painting_title=new.painting_title or existing.painting_title,
    )
    for key in ("v1", "v2"):
        old_v = existing.variant(key)  # type: ignore[arg-type]
        new_v = new.variant(key)  # type: ignore[arg-type]
        if variant_needs_regeneration(old_v):
            setattr(merged, key, new_v)
        else:
            setattr(merged, key, old_v)
    return merged


# Kompatybilnosc wsteczna
DescriptionDraftResult = ProductDescriptionDrafts


def format_draft_display(akapity: list[str]) -> str:
    """Tekst do podgladu / schowka — akapity rozdzielone pusta linia."""
    return "\n\n".join(a.strip() for a in akapity if (a or "").strip())


def format_akapity_compare_json(akapity: list[str]) -> str:
    """JSON do schowka — wklej w porownywarce akapitow («Wklej calosc» / Ctrl+V)."""
    cleaned = [a.strip() for a in akapity if (a or "").strip()]
    if len(cleaned) < 3:
        raise ValueError(
            f"Minimum 3 akapity do JSON porownywarki (jest {len(cleaned)}).",
        )
    return json.dumps({"akapity": cleaned}, ensure_ascii=False, indent=2) + "\n"


def _resolve_title(row: dict) -> str:
    return str(row.get("painting_title") or row.get("product_title") or "").strip()


def _generate_variant(
    row: dict,
    *,
    prompt: str,
    model: str,
    api_key: str | None,
    image_bytes: bytes | None,
    mime_type: str,
    on_status: Callable[[str], None] | None,
    should_abort: Callable[[], bool] | None,
) -> DescriptionVariant:
    out = DescriptionVariant()
    try:
        if image_bytes:
            raw, used_model = generate_from_image_bytes(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt,
                api_key=api_key,
                model=model,
                on_status=on_status,
                should_abort=should_abort,
            )
        else:
            if on_status:
                on_status("Pobieram miniature produktu...")
            data, mime = fetch_image_bytes_for_row(row)
            raw, used_model = generate_from_image_bytes(
                image_bytes=data,
                mime_type=mime,
                prompt=prompt,
                api_key=api_key,
                model=model,
                on_status=on_status,
                should_abort=should_abort,
            )
    except GeminiAborted:
        raise
    except Exception as exc:
        out.error = format_gemini_error(exc)
        return out

    try:
        akapity = parse_full_akapity_json(raw)
    except ValueError as exc:
        out.model_used = used_model
        out.raw_response = raw
        out.error = f"Nie udalo sie sparsowac JSON: {exc}"
        return out

    out.model_used = used_model
    out.raw_response = raw
    out.akapity = akapity
    out.generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return out


def process_product_descriptions(
    row: dict,
    *,
    model: str,
    api_key: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    on_status: Callable[[str], None] | None = None,
    should_abort: Callable[[], bool] | None = None,
    existing: ProductDescriptionDrafts | None = None,
) -> ProductDescriptionDrafts:
    """Gemini: obraz + «Opis z obrazu» v1 i v2 -> dwa warianty opisu."""
    pid = int(row.get("product_id") or 0)
    artist = str(row.get("artist") or "").strip()
    painting_title = _resolve_title(row)
    base = ProductDescriptionDrafts(
        product_id=pid,
        artist=artist,
        painting_title=painting_title,
    )
    if not artist:
        err = "Brak artysty w danych produktu."
        base.v1.error = err
        base.v2.error = err
        return base
    if not painting_title:
        err = "Brak tytulu obrazu w danych produktu."
        base.v1.error = err
        base.v2.error = err
        return base

    def _status_v1(msg: str) -> None:
        if on_status:
            on_status(f"{VARIANT_LABELS['v1']}: {msg}")

    if existing and not variant_needs_regeneration(existing.v1):
        base.v1 = existing.v1
    else:
        base.v1 = _generate_variant(
            row,
            prompt=build_image_description_prompt(artist=artist, title=painting_title),
            model=model,
            api_key=api_key,
            image_bytes=image_bytes,
            mime_type=mime_type,
            on_status=_status_v1,
            should_abort=should_abort,
        )

    if should_abort and should_abort():
        raise GeminiAborted("Przerwano przed generowaniem v2.")

    def _status_v2(msg: str) -> None:
        if on_status:
            on_status(f"{VARIANT_LABELS['v2']}: {msg}")

    if existing and not variant_needs_regeneration(existing.v2):
        base.v2 = existing.v2
    else:
        base.v2 = _generate_variant(
            row,
            prompt=build_image_description_prompt_v2(artist=artist, title=painting_title),
            model=model,
            api_key=api_key,
            image_bytes=image_bytes,
            mime_type=mime_type,
            on_status=_status_v2,
            should_abort=should_abort,
        )
    return base


def process_description_row(
    row: dict,
    *,
    model: str,
    api_key: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    on_status: Callable[[str], None] | None = None,
    should_abort: Callable[[], bool] | None = None,
    existing: ProductDescriptionDrafts | None = None,
) -> ProductDescriptionDrafts:
    """Generuje oba warianty opisu (v1 + v2); pomija warianty juz poprawne w `existing`."""
    return process_product_descriptions(
        row,
        model=model,
        api_key=api_key,
        image_bytes=image_bytes,
        mime_type=mime_type,
        on_status=on_status,
        should_abort=should_abort,
        existing=existing,
    )


__all__ = [
    "DescriptionDraftResult",
    "DescriptionVariant",
    "DescriptionVariantKey",
    "ProductDescriptionDrafts",
    "VARIANT_LABELS",
    "format_akapity_compare_json",
    "format_draft_display",
    "merge_description_drafts",
    "prefetch_row_images",
    "process_description_row",
    "process_product_descriptions",
    "variant_needs_regeneration",
]
