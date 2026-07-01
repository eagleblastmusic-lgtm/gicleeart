"""Yale Center for British Art — IIIF manifesty (pobieranie)."""

from __future__ import annotations

import re

from .http import get_json

_YALE_MANIFEST = "https://manifests.collections.yale.edu/ycba/obj/{oid}"


def yale_object_id_from_url(url: str) -> str:
    u = url or ""
    for pattern in (r"/catalog/tms:(\d+)", r"/obj/(\d+)", r"tms:(\d+)"):
        m = re.search(pattern, u, re.I)
        if m:
            return m.group(1)
    return ""


def yale_catalog_url(object_id: str) -> str:
    oid = (object_id or "").strip()
    return f"https://collections.britishart.yale.edu/catalog/tms:{oid}" if oid else ""


def _walk(obj: object):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def parse_yale_manifest(manifest: dict) -> dict[str, str]:
    label = manifest.get("label") or ""
    if isinstance(label, dict):
        title = str(label.get("en")[0] if isinstance(label.get("en"), list) else label.get("en") or "")
    elif isinstance(label, list) and label:
        title = str(label[0])
    else:
        title = str(label or "").strip()

    service_id = ""
    preview = ""
    for block in _walk(manifest):
        if not isinstance(block, dict):
            continue
        body = block.get("body")
        if isinstance(body, dict):
            services = body.get("service") or []
            if isinstance(services, dict):
                services = [services]
            for svc in services:
                if isinstance(svc, dict):
                    sid = str(svc.get("@id") or svc.get("id") or "").strip()
                    if sid and "images.collections.yale.edu" in sid:
                        service_id = sid
                        preview = str(body.get("id") or "").strip()
                        break
        if service_id:
            break

    oid = yale_object_id_from_url(str(manifest.get("id") or manifest.get("@id") or ""))
    if not oid:
        oid = yale_object_id_from_url(str(manifest.get("seeAlso") or ""))

    return {
        "title": title,
        "service_id": service_id,
        "preview_url": preview or (f"{service_id}/full/!400,400/0/default.jpg" if service_id else ""),
        "object_url": yale_catalog_url(oid),
        "raw_id": oid,
    }


def fetch_yale_manifest(object_id: str) -> dict[str, str]:
    oid = (object_id or "").strip()
    if not oid:
        return {}
    manifest = get_json(_YALE_MANIFEST.format(oid=oid), timeout=25)
    if not isinstance(manifest, dict):
        return {}
    return parse_yale_manifest(manifest)
