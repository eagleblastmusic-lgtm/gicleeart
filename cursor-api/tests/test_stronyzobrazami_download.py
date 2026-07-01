"""Testy silnika pobierania obrazow stronyzobrazami."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_iiif_service_from_preview_url() -> None:
    from Komponenty.stronyzobrazami.search.download.iiif_engine import iiif_service_from_url

    url = "https://www.artic.edu/iiif/2/abc/full/200,/0/default.jpg"
    assert iiif_service_from_url(url) == "https://www.artic.edu/iiif/2/abc"
    bel = "https://sammlung.belvedere.at/apis/iiif/image/v2/70888/full/!300,300/0/default.jpg"
    assert iiif_service_from_url(bel).endswith("/70888")


def test_resolve_artic_hit(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_hit

    def fake_get_json(url, **kwargs):
        assert "/16568" in url
        return {"data": {"image_id": "uuid-123", "title": "Starry Night", "artist_display": "Van Gogh"}}

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.download.resolvers.get_json",
        fake_get_json,
    )
    hit = ArtworkHit(
        source_id="artic",
        source_name="Artic",
        title="Starry Night",
        object_url="https://www.artic.edu/artworks/16568",
        raw_id="16568",
    )
    spec = resolve_hit(hit)
    assert spec is not None
    assert spec.strategy == "iiif"
    assert spec.service_id.endswith("/uuid-123")
    assert "Referer" in spec.headers


def test_resolve_url_direct_image() -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_url

    spec = resolve_url("https://images.example.org/foo/bar/master.jpg")
    assert spec is not None
    assert spec.strategy == "direct"
    assert spec.direct_url.endswith("master.jpg")


def test_resolve_url_newfields_artwork(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_url

    def fake_post_json(url, payload, **kwargs):
        return {
            "results": [
                {
                    "__typename": "Artwork",
                    "artwork_id": "53415",
                    "images": [{"iiif_url": "https://iiif.discovernewfields.org/iiif/3/53415-abc"}],
                },
            ],
        }

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.download.resolvers.post_json",
        fake_post_json,
    )
    spec = resolve_url("https://collections.discovernewfields.org/art/artwork/53415")
    assert spec is not None
    assert spec.strategy == "iiif"
    assert "53415" in spec.service_id


def test_sanitize_filename() -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import sanitize_filename

    assert sanitize_filename('Claude Monet — Bridge').endswith(".jpg")
    assert "<" not in sanitize_filename("a<b>c")


def test_resolve_mia_uses_large_cdn() -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_hit

    hit = ArtworkHit(
        source_id="mia",
        source_name="Mia",
        title="Test",
        object_url="https://collections.artsmia.org/art/10436",
        raw_id="10436",
    )
    spec = resolve_hit(hit)
    assert spec is not None
    assert spec.strategy == "direct"
    assert "/800/10436.jpg" in spec.direct_url


def test_resolve_cleveland_prefers_print(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_hit

    def fake_get_json(url, **kwargs):
        return {
            "images": {
                "web": {"url": "https://cdn.example/web.jpg"},
                "print": {"url": "https://cdn.example/print.jpg"},
            },
        }

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.download.resolvers.get_json",
        fake_get_json,
    )
    hit = ArtworkHit(
        source_id="cleveland",
        source_name="Cleveland",
        title="Test",
        object_url="https://www.clevelandart.org/art/1943.660",
        accession="1943.660",
    )
    spec = resolve_hit(hit)
    assert spec is not None
    assert spec.direct_url.endswith("print.jpg")


def test_resolve_smithsonian_hit(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_hit

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.download.resolvers.smithsonian_image_url",
        lambda oid, **kwargs: f"https://ids.si.edu/ids/deliveryService?id={oid}&max=0",
    )
    hit = ArtworkHit(
        source_id="smithsonian",
        source_name="Smithsonian",
        title="Water Lilies",
        object_url="https://www.si.edu/object/SAAM_1",
        raw_id="SAAM_1",
    )
    spec = resolve_hit(hit)
    assert spec is not None
    assert spec.strategy == "direct"
    assert "max=0" in spec.direct_url


def test_resolve_birmingham_trust_uses_assetbank_post() -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_hit

    hit = ArtworkHit(
        source_id="birmingham_trust",
        source_name="Birmingham Museums Trust",
        title="1909P62 Waiting",
        artist="John Everett Millais",
        object_url="https://dams.birminghammuseums.org.uk/assetbank-birminghammuseums/action/viewAsset?id=3455",
        image_url="https://d2cbqpmhv5w176.cloudfront.net/birmingham/thumb.jpg-s.jpg?sig=2",
        raw_id="3455",
    )
    spec = resolve_hit(hit)
    assert spec is not None
    assert spec.strategy == "assetbank_post"
    assert "viewAsset?id=3455" in spec.page_url


def test_resolve_url_birmingham_view_asset() -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_url

    spec = resolve_url(
        "https://dams.birminghammuseums.org.uk/assetbank-birminghammuseums/action/viewAsset?id=3493",
    )
    assert spec is not None
    assert spec.strategy == "assetbank_post"
    assert "3493" in spec.page_url


def test_resolve_url_cleveland_and_nga() -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_url

    nga = resolve_url("https://www.nga.gov/collection/art-object-page.12345.html")
    assert nga is not None
    assert nga.strategy in ("iiif", "page_scrape")
    assert nga.source_id == "nga"

    cle = resolve_url("https://www.clevelandart.org/art/1943.660")
    assert cle is not None
    assert cle.strategy in ("direct", "page_scrape")
    assert cle.source_id == "cleveland"


def test_resolve_rijks_slug_page_url(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.download.resolvers import resolve_url

    sample_obj = {
        "id": "https://id.rijksmuseum.nl/200109794",
        "shows": [{"id": "https://id.rijksmuseum.nl/visual/1"}],
    }

    def fake_fetch(ref: str):
        return sample_obj

    def fake_iiif(obj, *, cache=None):
        return "https://iiif.micr.io/vjYfT/full/180,/0/default.jpg"

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.rijks_lod.fetch_rijks_object",
        fake_fetch,
    )
    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.rijks_lod.rijks_iiif_service",
        lambda obj, **kwargs: "https://iiif.micr.io/vjYfT",
    )
    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.rijks_lod.rijks_image_url",
        fake_iiif,
    )

    url = "https://www.rijksmuseum.nl/nl/collectie/object/Zelfportret--72f97ac66c33f86b161cd51d62f7d365"
    spec = resolve_url(url)
    assert spec is not None
    assert spec.strategy == "iiif"
    assert "iiif.micr.io" in spec.service_id


def test_download_direct_cancel(monkeypatch, tmp_path) -> None:
    from Komponenty.stronyzobrazami.search.download.engine import download_spec
    from Komponenty.stronyzobrazami.search.download.types import DownloadSpec

    cancelled = {"n": 0}

    def cancel_check() -> bool:
        cancelled["n"] += 1
        return cancelled["n"] > 0

    spec = DownloadSpec(strategy="direct", direct_url="https://example.org/x.jpg")
    result = download_spec(spec, tmp_path, cancel_check=cancel_check)
    assert not result.ok
    assert "Anulowano" in (result.error or "")
