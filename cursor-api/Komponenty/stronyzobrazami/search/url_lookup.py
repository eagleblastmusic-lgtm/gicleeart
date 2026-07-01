"""Lookup ArtworkHit po URL strony muzeum (z reverse image search)."""

from __future__ import annotations

import re

from .adapters import MET_BASE, _cleveland_image_url
from .artic_images import artic_preview_url
from .http import get_json
from .mia_images import mia_preview_url
from .registry import source_for_url
from .rijks_lod import fetch_rijks_object, parse_rijks_object
from .types import ArtworkHit


def _id_from_url(url: str, pattern: str) -> str:
    m = re.search(pattern, url, re.I)
    return m.group(1) if m else ""


def _minimal_hit(
    *,
    source_id: str,
    source_name: str,
    object_url: str,
    title: str = "",
    raw_id: str = "",
) -> ArtworkHit:
    return ArtworkHit(
        source_id=source_id,
        source_name=source_name,
        title=title or object_url.rsplit("/", 1)[-1],
        object_url=object_url,
        search_mode="api",
        score=50.0,
        raw_id=raw_id,
    )


def lookup_hit_from_url(url: str, *, hint_title: str = "") -> ArtworkHit | None:
    raw = (url or "").strip()
    if not raw:
        return None
    src = source_for_url(raw)
    if not src:
        return None

    try:
        if src.source_id == "met":
            oid = _id_from_url(raw, r"/objects/(\d+)") or _id_from_url(raw, r"/(\d{5,})(?:\?|$)")
            if not oid:
                return _minimal_hit(
                    source_id="met",
                    source_name=src.name,
                    object_url=raw,
                    title=hint_title,
                )
            obj = get_json(f"{MET_BASE}/objects/{oid}", timeout=20)
            if not isinstance(obj, dict):
                return None
            img = str(obj.get("primaryImage") or obj.get("primaryImageSmall") or "")
            return ArtworkHit(
                source_id="met",
                source_name=src.name,
                title=str(obj.get("title") or hint_title or oid),
                artist=str(obj.get("artistDisplayName") or ""),
                date=str(obj.get("objectDate") or ""),
                medium=str(obj.get("medium") or ""),
                object_url=str(obj.get("objectURL") or raw),
                image_url=img,
                department=str(obj.get("department") or ""),
                object_type=str(obj.get("classification") or obj.get("objectName") or ""),
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "artic":
            oid = _id_from_url(raw, r"/artworks/(\d+)")
            if not oid:
                return _minimal_hit(source_id="artic", source_name=src.name, object_url=raw, title=hint_title)
            data = get_json(
                f"https://api.artic.edu/api/v1/artworks/{oid}?fields=id,title,artist_display,date_display,medium_display,image_id,artwork_type_title",
                timeout=20,
            )
            row = (data or {}).get("data") or {}
            if not isinstance(row, dict):
                return None
            img_id = row.get("image_id")
            return ArtworkHit(
                source_id="artic",
                source_name=src.name,
                title=str(row.get("title") or hint_title or oid),
                artist=str(row.get("artist_display") or ""),
                date=str(row.get("date_display") or ""),
                medium=str(row.get("medium_display") or ""),
                object_url=f"https://www.artic.edu/artworks/{oid}",
                image_url=artic_preview_url(str(img_id)) if img_id else "",
                object_type=str(row.get("artwork_type_title") or ""),
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "rijks":
            obj = fetch_rijks_object(raw)
            if not obj:
                return _minimal_hit(source_id="rijks", source_name=src.name, object_url=raw, title=hint_title)
            parsed_obj = parse_rijks_object(obj)
            return ArtworkHit(
                source_id="rijks",
                source_name=src.name,
                title=parsed_obj["title"] or hint_title,
                artist=parsed_obj["artist"],
                date=parsed_obj["date"],
                object_url=parsed_obj["object_url"] or raw,
                image_url=parsed_obj["image_url"],
                accession=parsed_obj["accession"],
                object_type=parsed_obj["object_type"],
                search_mode="api",
                score=70.0,
                raw_id=parsed_obj["raw_id"],
            )

        if src.source_id == "cleveland":
            acc = _id_from_url(raw, r"/art/([^/?#]+)")
            if not acc:
                return _minimal_hit(source_id="cleveland", source_name=src.name, object_url=raw, title=hint_title)
            data = get_json(f"https://openaccess-api.clevelandart.org/api/artworks/{acc}", timeout=20)
            row = (data or {}).get("data") or {}
            if not isinstance(row, dict):
                return None
            creators = row.get("creators") or []
            adn = str((creators[0] or {}).get("description") or "") if creators else ""
            return ArtworkHit(
                source_id="cleveland",
                source_name=src.name,
                title=str(row.get("title") or hint_title or acc),
                artist=adn,
                date=str(row.get("creation_date") or ""),
                medium=str(row.get("technique") or ""),
                object_url=str(row.get("url") or raw),
                image_url=_cleveland_image_url(row.get("images") or {}),
                accession=acc,
                search_mode="api",
                score=70.0,
                raw_id=str(row.get("id") or acc),
            )

        if src.source_id == "mia":
            oid = _id_from_url(raw, r"/art/(\d+)")
            if not oid:
                return _minimal_hit(source_id="mia", source_name=src.name, object_url=raw, title=hint_title)
            data = get_json(f"https://search.artsmia.org/id/{oid}", timeout=20)
            row = (data or {}).get("hits", {}).get("hits", [{}])[0].get("_source") or {}
            if not isinstance(row, dict):
                row = {}
            title = str(row.get("title") or hint_title or oid)
            return ArtworkHit(
                source_id="mia",
                source_name=src.name,
                title=title,
                artist=str(row.get("artist") or ""),
                date=str(row.get("dated") or ""),
                object_url=f"https://collections.artsmia.org/art/{oid}",
                image_url=mia_preview_url(oid),
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "belvedere":
            oid = _id_from_url(raw, r"/objects/(\d+)")
            if not oid:
                return _minimal_hit(source_id="belvedere", source_name=src.name, object_url=raw, title=hint_title)
            from .belvedere_iiif import parse_belvedere_manifest

            manifest = get_json(f"https://sammlung.belvedere.at/apis/iiif/presentation/v2/record/{oid}/manifest", timeout=20)
            parsed = parse_belvedere_manifest(manifest if isinstance(manifest, dict) else {})
            return ArtworkHit(
                source_id="belvedere",
                source_name=src.name,
                title=parsed.get("title") or hint_title or oid,
                artist=parsed.get("artist") or "",
                date=parsed.get("date") or "",
                object_url=f"https://sammlung.belvedere.at/objects/{oid}",
                image_url=parsed.get("image_url") or "",
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "albertina":
            oid = _id_from_url(raw, r"/objects/(\d+)")
            if not oid:
                return _minimal_hit(source_id="albertina", source_name=src.name, object_url=raw, title=hint_title)
            from .iiif_presentation_search import parse_iiif_manifest

            manifest = get_json(
                f"https://sammlungenonline.albertina.at/apis/iiif/presentation/v2/1-objects-{oid}/manifest",
                timeout=20,
            )
            parsed = parse_iiif_manifest(manifest if isinstance(manifest, dict) else {})
            return ArtworkHit(
                source_id="albertina",
                source_name=src.name,
                title=parsed.get("title") or hint_title or oid,
                artist=parsed.get("artist") or "",
                date=parsed.get("date") or "",
                object_url=raw,
                image_url=parsed.get("image_url") or "",
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "newfields":
            oid = _id_from_url(raw, r"/artwork/(\d+)")
            if not oid:
                return _minimal_hit(source_id="newfields", source_name=src.name, object_url=raw, title=hint_title)
            from .newfields_api import (
                newfields_artwork_meta,
                newfields_artwork_url,
                newfields_creators,
                newfields_date,
                newfields_image_url,
            )

            object_type, medium = newfields_artwork_meta(oid)
            data = get_json(f"https://collections.discovernewfields.org/api/artworks/{oid}", timeout=20)
            row = (data or {}).get("data") or data or {}
            if not isinstance(row, dict):
                row = {}
            title = str(row.get("title") or hint_title or oid)
            return ArtworkHit(
                source_id="newfields",
                source_name=src.name,
                title=title,
                artist=newfields_creators(row) if row else "",
                date=newfields_date(row) if row else "",
                object_url=newfields_artwork_url(oid) or raw,
                image_url=newfields_image_url(row) if row else "",
                object_type=object_type,
                medium=medium,
                search_mode="api",
                score=70.0,
                raw_id=str(oid),
            )

        if src.source_id == "smk":
            oid = _id_from_url(raw, r"/artwork/image/([^/?#]+)") or _id_from_url(raw, r"/(\d{5,})")
            return _minimal_hit(
                source_id="smk",
                source_name=src.name,
                object_url=raw,
                title=hint_title,
                raw_id=oid,
            )

        if src.source_id == "getty":
            return _minimal_hit(source_id="getty", source_name=src.name, object_url=raw, title=hint_title)

        if src.source_id == "smithsonian":
            oid = _id_from_url(raw, r"/object/([A-Za-z0-9:_-]+)") or _id_from_url(raw, r"/detail/([A-Za-z0-9:_-]+)")
            return _minimal_hit(
                source_id="smithsonian",
                source_name=src.name,
                object_url=raw,
                title=hint_title,
                raw_id=oid,
            )

        if src.source_id in ("nga", "walters", "yale"):
            return _minimal_hit(
                source_id=src.source_id,
                source_name=src.name,
                object_url=raw,
                title=hint_title,
            )

    except RuntimeError:
        return _minimal_hit(
            source_id=src.source_id,
            source_name=src.name,
            object_url=raw,
            title=hint_title,
        )

    return _minimal_hit(source_id=src.source_id, source_name=src.name, object_url=raw, title=hint_title)
