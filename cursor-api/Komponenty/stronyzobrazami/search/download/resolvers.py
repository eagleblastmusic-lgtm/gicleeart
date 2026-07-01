"""Rozpoznawanie najlepszego sposobu pobrania obrazu (per zrodlo / URL)."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from ..artic_images import ARTIC_IIIF_BASE, artic_fetch_headers
from ..belvedere_iiif import parse_belvedere_manifest
from ..iiif_presentation_search import parse_iiif_manifest
from ..http import USER_AGENT, get_json, post_json
from ..mia_images import mia_preview_url
from ..nga_images import nga_iiif_service
from ..newfields_api import NEWFIELDS_SEARCH
from ..smithsonian_media import smithsonian_image_url
from ..walters_images import walters_download_url
from ..yale_iiif import fetch_yale_manifest, yale_object_id_from_url
from ..registry import source_for_url
from ..types import ArtworkHit
from .cache import cached
from .iiif_engine import iiif_service_from_url, normalize_iiif_service
from .types import DownloadSpec

MET_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
ARTIC_API = "https://api.artic.edu/api/v1/artworks"
CLEVELAND_API = "https://openaccess-api.clevelandart.org/api/artworks/"
SMK_API = "https://api.smk.dk/api/v1/art/"


def _cleveland_image_url(images: dict) -> str:
    if not isinstance(images, dict):
        return ""
    for key in ("print", "web", "full"):
        block = images.get(key) or {}
        if isinstance(block, dict):
            url = str(block.get("url") or block.get("full") or "").strip()
            if url:
                return url
    return ""

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def sanitize_filename(text: str, *, ext: str = ".jpg") -> str:
    base = _INVALID_FILENAME.sub(" ", (text or "").strip())
    base = re.sub(r"\s+", " ", base).strip(" .") or "obraz"
    if len(base) > 120:
        base = base[:120].rstrip()
    if not ext.startswith("."):
        ext = f".{ext}"
    return f"{base}{ext}"


def _spec(
    *,
    strategy: str,
    title: str = "",
    artist: str = "",
    source_id: str = "",
    service_id: str = "",
    direct_url: str = "",
    page_url: str = "",
    headers: dict[str, str] | None = None,
    filename: str = "",
) -> DownloadSpec:
    label = " — ".join(x for x in (artist, title) if x).strip() or title or "obraz"
    return DownloadSpec(
        strategy=strategy,  # type: ignore[arg-type]
        source_id=source_id,
        title=title,
        artist=artist,
        service_id=service_id,
        direct_url=direct_url,
        page_url=page_url,
        headers=headers or {},
        suggested_filename=sanitize_filename(filename or label),
    )


def _id_from_url(url: str, pattern: str) -> str:
    m = re.search(pattern, url or "")
    return m.group(1) if m else ""


def _resolve_met(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/objects/(\d+)")
    if not oid:
        return None
    obj = get_json(f"{MET_BASE}/objects/{oid}", timeout=20)
    url = str(obj.get("primaryImage") or obj.get("primaryImageSmall") or "").strip()
    if not url:
        return None
    return _spec(
        strategy="direct",
        source_id="met",
        title=hit.title,
        artist=hit.artist,
        direct_url=url,
        filename=f"{hit.artist} — {hit.title}" if hit.artist else hit.title,
    )


def _resolve_artic(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/artworks/(\d+)")
    if not oid:
        if hit.image_url and "artic.edu/iiif/" in hit.image_url:
            return _spec(
                strategy="iiif",
                source_id="artic",
                title=hit.title,
                artist=hit.artist,
                service_id=iiif_service_from_url(hit.image_url),
                headers=artic_fetch_headers(artwork_id=oid or None),
            )
        return None
    data = get_json(f"{ARTIC_API}/{oid}?fields=id,image_id,title,artist_display", timeout=20)
    row = (data or {}).get("data") or {}
    image_id = str(row.get("image_id") or "").strip()
    if not image_id:
        return None
    return _spec(
        strategy="iiif",
        source_id="artic",
        title=hit.title or str(row.get("title") or ""),
        artist=hit.artist or str(row.get("artist_display") or ""),
        service_id=f"{ARTIC_IIIF_BASE}/{image_id}",
        headers=artic_fetch_headers(artwork_id=oid),
    )


def _resolve_cleveland(hit: ArtworkHit) -> DownloadSpec | None:
    acc = hit.accession or _id_from_url(hit.object_url, r"/art/([^/?#]+)")
    if not acc:
        if hit.image_url:
            return _spec(strategy="direct", source_id="cleveland", direct_url=hit.image_url, title=hit.title, artist=hit.artist)
        return None
    obj = get_json(f"{CLEVELAND_API}{urllib.parse.quote(acc, safe='')}", timeout=20)
    images = (obj or {}).get("images") or {}
    url = _cleveland_image_url(images) or str(hit.image_url or "").strip()
    if not url:
        return None
    return _spec(strategy="direct", source_id="cleveland", direct_url=url, title=hit.title, artist=hit.artist)


def _resolve_mia(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/art/(\d+)")
    if not oid:
        return None
    url = mia_preview_url(oid, large=True)
    if not url:
        return None
    return _spec(strategy="direct", source_id="mia", direct_url=url, title=hit.title, artist=hit.artist)


def _resolve_rijks(hit: ArtworkHit) -> DownloadSpec | None:
    if hit.image_url and "iiif" in hit.image_url.lower():
        service = iiif_service_from_url(hit.image_url.replace("/full/180,/", "/full/max/"))
        return _spec(strategy="iiif", source_id="rijks", service_id=service, title=hit.title, artist=hit.artist)
    from ..rijks_lod import fetch_rijks_object, rijks_iiif_service

    ref = hit.raw_id or hit.object_url
    obj = fetch_rijks_object(ref) if ref else None
    if obj:
        service = rijks_iiif_service(obj)
        if service:
            return _spec(
                strategy="iiif",
                source_id="rijks",
                service_id=iiif_service_from_url(service),
                title=hit.title,
                artist=hit.artist,
            )
    return None


def _resolve_belvedere(hit: ArtworkHit) -> DownloadSpec | None:
    if hit.image_url:
        return _spec(
            strategy="iiif",
            source_id="belvedere",
            service_id=iiif_service_from_url(hit.image_url),
            title=hit.title,
            artist=hit.artist,
        )
    oid = hit.raw_id
    if oid:
        manifest = get_json(
            f"https://sammlung.belvedere.at/apis/iiif/presentation/v2/1-objects-{oid}/manifest",
            timeout=20,
        )
        parsed = parse_belvedere_manifest(manifest if isinstance(manifest, dict) else {})
        if parsed.get("image_url"):
            return _spec(
                strategy="iiif",
                source_id="belvedere",
                service_id=iiif_service_from_url(parsed["image_url"]),
                title=parsed.get("title") or hit.title,
                artist=parsed.get("artist") or hit.artist,
            )
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="belvedere", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_albertina(hit: ArtworkHit) -> DownloadSpec | None:
    if hit.image_url:
        return _spec(
            strategy="iiif",
            source_id="albertina",
            service_id=iiif_service_from_url(hit.image_url),
            title=hit.title,
            artist=hit.artist,
        )
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/objects/(\d+)")
    if oid:
        manifest = get_json(
            f"https://sammlungenonline.albertina.at/apis/iiif/presentation/v2/1-objects-{oid}/manifest",
            timeout=20,
        )
        parsed = parse_iiif_manifest(manifest if isinstance(manifest, dict) else {})
        if parsed.get("image_url"):
            return _spec(
                strategy="iiif",
                source_id="albertina",
                service_id=iiif_service_from_url(parsed["image_url"]),
                title=parsed.get("title") or hit.title,
                artist=parsed.get("artist") or hit.artist,
            )
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="albertina", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_newfields(hit: ArtworkHit) -> DownloadSpec | None:
    if hit.image_url:
        service = iiif_service_from_url(hit.image_url.replace("__small", ""))
        return _spec(strategy="iiif", source_id="newfields", service_id=service, title=hit.title, artist=hit.artist)
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/artwork/(\d+)")
    if oid:
        data = post_json(NEWFIELDS_SEARCH, {"searchTerm": oid, "from": 0}, timeout=20)
        for row in (data or {}).get("results") or []:
            if str(row.get("artwork_id") or "") != str(oid):
                continue
            images = row.get("images") or []
            if images and isinstance(images[0], dict):
                url = str(images[0].get("iiif_url") or "").strip()
                if url:
                    return _spec(strategy="iiif", source_id="newfields", service_id=normalize_iiif_service(url), title=hit.title, artist=hit.artist)
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="newfields", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_getty(hit: ArtworkHit) -> DownloadSpec | None:
    if hit.image_url and "media.getty.edu/iiif/image/" in hit.image_url:
        return _spec(
            strategy="iiif",
            source_id="getty",
            service_id=iiif_service_from_url(hit.image_url),
            title=hit.title,
            artist=hit.artist,
        )
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="getty", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_smk(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/image/([^/?#]+)")
    if oid:
        obj = get_json(f"{SMK_API}{oid}?lang=en", timeout=20)
        for img in (obj or {}).get("images") or []:
            if isinstance(img, dict) and img.get("uri"):
                uri = str(img["uri"])
                if "iiif" in uri.lower() or "/full/" in uri:
                    return _spec(strategy="iiif", source_id="smk", service_id=iiif_service_from_url(uri), title=hit.title, artist=hit.artist)
                return _spec(strategy="direct", source_id="smk", direct_url=uri, title=hit.title, artist=hit.artist)
    if hit.image_url:
        if "iiif" in hit.image_url.lower():
            return _spec(strategy="iiif", source_id="smk", service_id=iiif_service_from_url(hit.image_url), title=hit.title, artist=hit.artist)
        return _spec(strategy="direct", source_id="smk", direct_url=hit.image_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_smithsonian(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/object/([^/?#]+)")
    if oid:
        url = smithsonian_image_url(oid, large=True)
        if url:
            return _spec(
                strategy="direct",
                source_id="smithsonian",
                direct_url=url,
                title=hit.title,
                artist=hit.artist,
            )
    if hit.image_url:
        return _spec(
            strategy="direct",
            source_id="smithsonian",
            direct_url=_upgrade_smithsonian_url(hit.image_url),
            title=hit.title,
            artist=hit.artist,
        )
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="smithsonian", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _upgrade_smithsonian_url(url: str) -> str:
    u = (url or "").strip()
    if "deliveryService" in u and "&max=" not in u:
        return f"{u}&max=0"
    return u


def _resolve_nga(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"art-object-page\.(\d+)\.html")
    service = nga_iiif_service(oid) if oid else ""
    if service:
        return _spec(
            strategy="iiif",
            source_id="nga",
            service_id=normalize_iiif_service(service),
            title=hit.title,
            artist=hit.artist,
        )
    page = hit.object_url or (f"https://www.nga.gov/collection/art-object-page.{oid}.html" if oid else "")
    if page:
        return _spec(strategy="page_scrape", source_id="nga", page_url=page, title=hit.title, artist=hit.artist)
    return None


def _resolve_walters(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or _id_from_url(hit.object_url, r"/detail/(\d+)")
    if oid:
        url = walters_download_url(oid)
        if url:
            return _spec(
                strategy="direct",
                source_id="walters",
                direct_url=url,
                title=hit.title,
                artist=hit.artist,
            )
    page = hit.object_url or (f"https://art.thewalters.org/detail/{oid}" if oid else "")
    if page:
        return _spec(strategy="page_scrape", source_id="walters", page_url=page, title=hit.title, artist=hit.artist)
    return None


def _resolve_yale(hit: ArtworkHit) -> DownloadSpec | None:
    oid = hit.raw_id or yale_object_id_from_url(hit.object_url)
    if oid:
        parsed = fetch_yale_manifest(oid)
        service = parsed.get("service_id") or ""
        if service:
            return _spec(
                strategy="iiif",
                source_id="yale",
                service_id=normalize_iiif_service(service),
                title=hit.title or parsed.get("title", ""),
                artist=hit.artist,
                page_url=parsed.get("object_url") or hit.object_url,
            )
    if hit.object_url:
        return _spec(strategy="page_scrape", source_id="yale", page_url=hit.object_url, title=hit.title, artist=hit.artist)
    return None


def _resolve_birmingham_trust(hit: ArtworkHit) -> DownloadSpec | None:
    page_url = (hit.object_url or "").strip()
    if not page_url and hit.raw_id:
        page_url = f"https://dams.birminghammuseums.org.uk/assetbank-birminghammuseums/action/viewAsset?id={hit.raw_id}"
    if not page_url:
        return None
    return _spec(
        strategy="assetbank_post",
        source_id="birmingham_trust",
        page_url=page_url,
        title=hit.title,
        artist=hit.artist,
    )


def _resolve_from_image_url(hit: ArtworkHit) -> DownloadSpec | None:
    url = (hit.image_url or "").strip()
    if not url:
        return None
    if hit.source_id == "birmingham_trust" and (".jpg-s.jpg" in url or "-s.jpg" in url):
        return None
    if "iiif" in url.lower() or "/full/" in url:
        headers = {}
        if "artic.edu" in url:
            headers = artic_fetch_headers()
        return _spec(
            strategy="iiif",
            source_id=hit.source_id,
            service_id=iiif_service_from_url(url),
            title=hit.title,
            artist=hit.artist,
            headers=headers,
        )
    return _spec(
        strategy="direct",
        source_id=hit.source_id,
        direct_url=url,
        title=hit.title,
        artist=hit.artist,
    )


_RESOLVE_HIT: dict[str, object] = {
    "met": _resolve_met,
    "artic": _resolve_artic,
    "cleveland": _resolve_cleveland,
    "mia": _resolve_mia,
    "rijks": _resolve_rijks,
    "belvedere": _resolve_belvedere,
    "albertina": _resolve_albertina,
    "newfields": _resolve_newfields,
    "getty": _resolve_getty,
    "smk": _resolve_smk,
    "smithsonian": _resolve_smithsonian,
    "nga": _resolve_nga,
    "walters": _resolve_walters,
    "yale": _resolve_yale,
    "birmingham_trust": _resolve_birmingham_trust,
}


def resolve_hit(hit: ArtworkHit) -> DownloadSpec | None:
    cache_key = f"hit:{hit.source_id}:{hit.raw_id}:{hit.object_url}:{hit.image_url}"
    return cached(cache_key, lambda: _resolve_hit_uncached(hit), ttl=300.0)


def _resolve_hit_uncached(hit: ArtworkHit) -> DownloadSpec | None:
    fn = _RESOLVE_HIT.get(hit.source_id)
    if fn:
        spec = fn(hit)  # type: ignore[operator]
        if spec and spec.ok:
            return spec
    if hit.image_url:
        spec = _resolve_from_image_url(hit)
        if spec and spec.ok:
            return spec
    if hit.object_url:
        return _spec(
            strategy="page_scrape",
            source_id=hit.source_id,
            page_url=hit.object_url,
            title=hit.title,
            artist=hit.artist,
        )
    return None


_IIIF_PAGE_PATTERNS = (
    r'"(?:service|@id)"\s*:\s*"(https?://[^"]+/iiif/(?:image/)?v?\d+/[^"]+)"',
    r'"(https?://[^"]+/iiif/2/[^"/]+)"',
    r'"(https?://[^"]+/apis/iiif/image/v2/\d+)"',
    r'"(https?://iiif\.discovernewfields\.org/iiif/3/[^"]+)"',
    r'"(https?://media\.getty\.edu/iiif/image/[^"]+)"',
    r"/server\.iip\?IIIF=[^\"' <]+",
    r"https?://[^\"' <]+\?IIIF=[^\"' <]+",
)


def scrape_page_for_iiif(
    page_url: str,
    *,
    timeout: float = 25.0,
    cancel_check: object = None,
) -> str:
    if cancel_check and cancel_check():  # type: ignore[operator]
        raise RuntimeError("Anulowano.")
    req = urllib.request.Request(page_url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace").replace("\\/", "/")
    for pattern in _IIIF_PAGE_PATTERNS:
        if cancel_check and cancel_check():  # type: ignore[operator]
            raise RuntimeError("Anulowano.")
        for match in re.findall(pattern, html, flags=re.IGNORECASE):
            service = normalize_iiif_service(match.split("/full/")[0].split('"')[0])
            if "iiif" in service.lower() or "iip" in service.lower():
                return service
    return ""


def _resolve_rijks_url(raw: str) -> DownloadSpec | None:
    from ..rijks_lod import fetch_rijks_object, rijks_iiif_service

    obj = fetch_rijks_object(raw)
    if not obj:
        return None
    service = rijks_iiif_service(obj)
    if not service:
        return None
    return _spec(strategy="iiif", source_id="rijks", service_id=iiif_service_from_url(service), page_url=raw)


def resolve_url(url: str) -> DownloadSpec | None:
    raw = (url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if not parsed.scheme:
        raw = "https://" + raw.lstrip("/")
        parsed = urlparse(raw)

    if raw.lower().endswith("/info.json"):
        return _spec(strategy="iiif", service_id=iiif_service_from_url(raw))

    if "/full/" in raw and ("iiif" in raw.lower() or "iip" in raw.lower()):
        headers = artic_fetch_headers() if "artic.edu" in raw else {}
        return _spec(strategy="iiif", service_id=iiif_service_from_url(raw), headers=headers)

    src = source_for_url(raw)
    source_id = src.source_id if src else ""

    if "discovernewfields.org" in parsed.netloc and "/art/artwork/" in raw:
        oid = _id_from_url(raw, r"/artwork/(\d+)")
        if oid:
            hit = ArtworkHit(
                source_id="newfields",
                source_name="Newfields",
                title="",
                object_url=raw,
                raw_id=oid,
            )
            spec = _resolve_newfields(hit)
            if spec and spec.ok:
                spec.page_url = raw
                return spec

    if "sammlung.belvedere.at" in parsed.netloc and "/objects/" in raw:
        oid = _id_from_url(raw, r"/objects/(\d+)")
        if oid:
            hit = ArtworkHit(
                source_id="belvedere",
                source_name="Belvedere",
                title="",
                object_url=raw,
                raw_id=oid,
            )
            return _resolve_belvedere(hit)

    if "sammlungenonline.albertina.at" in parsed.netloc and "/objects/" in raw:
        oid = _id_from_url(raw, r"/objects/(\d+)")
        if oid:
            hit = ArtworkHit(
                source_id="albertina",
                source_name="Albertina",
                title="",
                object_url=raw,
                raw_id=oid,
            )
            return _resolve_albertina(hit)

    if "metmuseum.org" in parsed.netloc:
        oid = _id_from_url(raw, r"/objects/(\d+)") or _id_from_url(raw, r"/(\d{5,})(?:\?|$)")
        if oid:
            return _resolve_met(
                ArtworkHit(source_id="met", source_name="Met", title="", object_url=raw, raw_id=oid),
            )

    if "artic.edu" in parsed.netloc and "/artworks/" in raw:
        oid = _id_from_url(raw, r"/artworks/(\d+)")
        if oid:
            return _resolve_artic(
                ArtworkHit(source_id="artic", source_name="Artic", title="", object_url=raw, raw_id=oid),
            )

    if "artsmia.org" in parsed.netloc:
        oid = _id_from_url(raw, r"/art/(\d+)")
        if oid:
            return _resolve_mia(
                ArtworkHit(source_id="mia", source_name="Mia", title="", object_url=raw, raw_id=oid),
            )

    if "clevelandart.org" in parsed.netloc and "/art/" in raw:
        acc = _id_from_url(raw, r"/art/([^/?#]+)")
        if acc:
            spec = _resolve_cleveland(
                ArtworkHit(source_id="cleveland", source_name="Cleveland", title="", object_url=raw, accession=acc),
            )
            if spec and spec.ok:
                return spec

    if "getty.edu" in parsed.netloc and "/object/" in raw:
        spec = _resolve_getty(
            ArtworkHit(source_id="getty", source_name="Getty", title="", object_url=raw),
        )
        if spec and spec.ok:
            return spec

    if "open.smk.dk" in parsed.netloc or "smk.dk" in parsed.netloc:
        oid = _id_from_url(raw, r"/image/([^/?#]+)")
        if oid:
            spec = _resolve_smk(
                ArtworkHit(source_id="smk", source_name="SMK", title="", object_url=raw, raw_id=oid),
            )
            if spec and spec.ok:
                return spec

    if "nga.gov" in parsed.netloc:
        oid = _id_from_url(raw, r"art-object-page\.(\d+)\.html")
        if oid:
            spec = _resolve_nga(
                ArtworkHit(source_id="nga", source_name="NGA", title="", object_url=raw, raw_id=oid),
            )
            if spec and spec.ok:
                return spec

    if "thewalters.org" in parsed.netloc:
        oid = _id_from_url(raw, r"/detail/(\d+)")
        if oid:
            spec = _resolve_walters(
                ArtworkHit(source_id="walters", source_name="Walters", title="", object_url=raw, raw_id=oid),
            )
            if spec and spec.ok:
                return spec

    if "rijksmuseum.nl" in parsed.netloc:
        spec = _resolve_rijks_url(raw)
        if spec and spec.ok:
            spec.page_url = raw
            return spec

    if "si.edu" in parsed.netloc:
        oid = _id_from_url(raw, r"/object/([^/?#]+)")
        if oid:
            spec = _resolve_smithsonian(
                ArtworkHit(source_id="smithsonian", source_name="Smithsonian", title="", object_url=raw, raw_id=oid),
            )
            if spec and spec.ok:
                return spec

    if "britishart.yale.edu" in parsed.netloc:
        oid = yale_object_id_from_url(raw)
        if oid:
            spec = _resolve_yale(
                ArtworkHit(source_id="yale", source_name="Yale", title="", object_url=raw, raw_id=oid),
            )
            if spec and spec.ok:
                return spec

    if "birminghammuseums.org.uk" in parsed.netloc and "viewAsset" in raw:
        oid = _id_from_url(raw, r"[?&]id=(\d+)")
        if oid:
            spec = _resolve_birmingham_trust(
                ArtworkHit(
                    source_id="birmingham_trust",
                    source_name="Birmingham Museums Trust",
                    title="",
                    object_url=raw,
                    raw_id=oid,
                ),
            )
            if spec and spec.ok:
                return spec

    if re.search(r"\.(jpg|jpeg|png|webp|tif|tiff)(\?|$)", raw, re.I):
        return _spec(strategy="direct", source_id=source_id, direct_url=raw)

    service = scrape_page_for_iiif(raw)
    if service:
        headers = artic_fetch_headers() if "artic.edu" in raw else {}
        return _spec(strategy="iiif", source_id=source_id, service_id=service, page_url=raw, headers=headers)

    return _spec(strategy="page_scrape", source_id=source_id, page_url=raw)
