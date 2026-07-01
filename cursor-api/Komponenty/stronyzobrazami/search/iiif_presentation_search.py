"""Wyszukiwanie przez IIIF Presentation API 2.x (Belvedere, Albertina…)."""

from __future__ import annotations

import re
import urllib.parse

ALBERTINA_IIIF_SEARCH = (
    "https://sammlungenonline.albertina.at/apis/iiif/presentation/v2/collection/search/objects"
)
BELVEDERE_IIIF_SEARCH = (
    "https://sammlung.belvedere.at/apis/iiif/presentation/v2/collection/search/objects"
)


def iiif_search_url(base: str, query: str, *, page: int = 1) -> str:
    encoded = urllib.parse.quote(query.strip(), safe="")
    base = base.rstrip("/")
    if page <= 1:
        return f"{base}/{encoded}"
    return f"{base}/{encoded}?page={page}"


def _first_link(items: object) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict):
            link = str(item.get("@id") or "").strip()
            if link:
                return link
    return ""


def parse_canvas_label(label: str) -> dict[str, str]:
    parts = [part.strip() for part in label.split(",") if part.strip()]
    out = {
        "artist": parts[0] if parts else "",
        "title": parts[1] if len(parts) > 1 else "",
        "date": parts[2] if len(parts) > 2 else "",
        "medium": parts[3] if len(parts) > 3 else "",
        "accession": "",
        "object_type": "",
    }
    for part in parts:
        match = re.search(r"Inv\.(?:-Nr\.?| Nr\.?)\s*:?\s*([0-9A-Za-z./-]+)", part, re.IGNORECASE)
        if match:
            out["accession"] = match.group(1).strip()
    medium = out["medium"].lower()
    if any(token in medium for token in ("öl auf leinwand", "oil on canvas", "öl auf", "acryl", "leinwand")):
        out["object_type"] = "Painting"
    elif any(token in medium for token in ("holzschnitt", "radierung", "lithographie", "druck", "print")):
        out["object_type"] = "Print"
    elif any(
        token in medium
        for token in ("zeichnung", "bleistift", "kohle", "feder", "tusche", "kreide", "pastell", "aquarell", "drawing")
    ):
        out["object_type"] = "Drawing"
    return out


def parse_iiif_manifest(manifest: dict, *, object_url_prefix: str = "") -> dict[str, str]:
    label = str(manifest.get("label") or "").strip()
    if label.lower() == "null":
        label = ""

    object_url = _first_link(manifest.get("related")) or _first_link(manifest.get("rendering"))
    canvas_label = ""
    image_url = ""
    sequences = manifest.get("sequences") or []
    if sequences and isinstance(sequences[0], dict):
        canvases = sequences[0].get("canvases") or []
        if canvases and isinstance(canvases[0], dict):
            canvas = canvases[0]
            canvas_label = str(canvas.get("label") or "").strip()
            images = canvas.get("images") or []
            if images and isinstance(images[0], dict):
                resource = images[0].get("resource")
                if isinstance(resource, dict):
                    service = resource.get("service")
                    if isinstance(service, dict):
                        service_id = str(service.get("@id") or "").strip()
                        if service_id:
                            image_url = f"{service_id}/full/!300,300/0/default.jpg"

    parsed = parse_canvas_label(canvas_label)
    title = label or parsed["title"]
    raw_id = ""
    manifest_id = str(manifest.get("@id") or "")
    match = re.search(r"1-objects-(\d+)/manifest", manifest_id)
    if match:
        raw_id = match.group(1)
        if not object_url and object_url_prefix and raw_id:
            object_url = f"{object_url_prefix.rstrip('/')}/{raw_id}"

    return {
        "title": title,
        "artist": parsed["artist"],
        "date": parsed["date"],
        "medium": parsed["medium"],
        "accession": parsed["accession"],
        "object_type": parsed["object_type"],
        "object_url": object_url,
        "image_url": image_url,
        "raw_id": raw_id,
    }
