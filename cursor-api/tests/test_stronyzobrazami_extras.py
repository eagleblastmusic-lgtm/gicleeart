"""Testy rozszerzen stronyzobrazami (score, dedup, obrazy, Yale)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_walters_preview_from_media_csv(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import walters_images as mod

    (tmp_path / "walters_media.csv").write_text(
        "ObjectID,MediaXrefID,ImageURL,Filename,MediaType,MediaView,Rank,IsPrimary\n"
        '7,9199,https://art.thewalters.org/images/raw/PS1_54.975_Fnt_DD_T08.jpg,PS1_54.975_Fnt_DD_T08.jpg,Image,Front,1,1\n'
        '7,9198,https://art.thewalters.org/images/raw/PS1_54.975_Back_DD_T08.jpg,PS1_54.975_Back_DD_T08.jpg,Image,Back,3,0\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "_CACHE", tmp_path / "walters_media.csv")
    mod._preview_by_object = None
    mod._download_by_object = None
    monkeypatch.setattr(mod, "ensure_cached_csv", lambda _u, dest: dest)

    url = mod.walters_preview_url("7")
    assert "Fnt_DD_T08" in url


def test_nga_preview_from_published_csv(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import nga_images as mod

    (tmp_path / "nga_published_images.csv").write_text(
        "uuid,iiifurl,iiifthumburl,viewtype,sequence,width,height,maxpixels,openaccess,created,modified,depictstmsobjectid,assistivetext\n"
        'u1,https://api.nga.gov/iiif/x,"https://api.nga.gov/iiif/x/full/!200,200/0/default.jpg",primary,1,1000,800,4096,1,,,45872,\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "_CACHE", tmp_path / "nga_published_images.csv")
    mod._by_object = None
    monkeypatch.setattr(mod, "ensure_cached_csv", lambda _u, dest: dest)

    assert "200" in mod.nga_preview_url("45872")
    assert mod.nga_iiif_service("45872").endswith("/x")


def test_score_and_dedupe() -> None:
    from Komponenty.stronyzobrazami.search.dedup import dedupe_hits
    from Komponenty.stronyzobrazami.search.score import apply_scores
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    hits = [
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Morning Haze",
            artist="Claude Monet",
            search_mode="api",
            image_url="http://x",
        ),
        ArtworkHit(
            source_id="nga",
            source_name="NGA",
            title="Morning Haze",
            artist="Claude Monet",
            search_mode="local",
        ),
    ]
    scored = apply_scores(hits, query_artist="Monet", query_title="Morning Haze")
    assert scored[0].score > 1.0
    merged = dedupe_hits(scored)
    assert len(merged) == 1
    assert "(+" in merged[0].source_name


def test_yale_manifest_parse() -> None:
    from Komponenty.stronyzobrazami.search.yale_iiif import parse_yale_manifest, yale_object_id_from_url

    assert yale_object_id_from_url("https://collections.britishart.yale.edu/catalog/tms:1772") == "1772"
    manifest = {
        "label": "Sample",
        "id": "https://manifests.collections.yale.edu/ycba/obj/1772",
        "items": [
            {
                "items": [
                    {
                        "body": {
                            "id": "https://images.collections.yale.edu/iiif/2/ycba:abc/full/full/0/default.jpg",
                            "service": [
                                {
                                    "@id": "https://images.collections.yale.edu/iiif/2/ycba:abc",
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }
    parsed = parse_yale_manifest(manifest)
    assert parsed["service_id"].endswith("ycba:abc")


def test_resolve_hit_cached(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.adapters import ArtworkHit
    from Komponenty.stronyzobrazami.search.download.cache import clear_cache
    from Komponenty.stronyzobrazami.search.download import resolvers as mod

    clear_cache()
    calls = {"n": 0}

    def fake_mia(hit):
        calls["n"] += 1
        return mod._spec(
            strategy="direct",
            source_id="mia",
            direct_url="https://example.org/x.jpg",
        )

    monkeypatch.setitem(mod._RESOLVE_HIT, "mia", fake_mia)
    hit = ArtworkHit(source_id="mia", source_name="Mia", title="X", raw_id="1")
    assert mod.resolve_hit(hit) is not None
    assert mod.resolve_hit(hit) is not None
    assert calls["n"] == 1


def test_force_png_applies_only_to_iiif() -> None:
    from Komponenty.stronyzobrazami.search.download.engine import png_option_applies
    from Komponenty.stronyzobrazami.search.download.types import DownloadSpec

    assert png_option_applies(DownloadSpec(strategy="iiif", service_id="https://x/y"))
    assert png_option_applies(DownloadSpec(strategy="page_scrape", page_url="https://x"))
    assert not png_option_applies(DownloadSpec(strategy="direct", direct_url="https://x/a.jpg"))
    assert not png_option_applies(None)


def test_force_png_dest_suffix_skipped_for_direct(tmp_path) -> None:
    from Komponenty.stronyzobrazami.search.download.engine import _dest_path

    direct = _dest_path(tmp_path, "obraz.jpg", force_png=True, strategy="direct")
    assert direct.suffix == ".jpg"
    iiif = _dest_path(tmp_path, "obraz.jpg", force_png=True, strategy="iiif")
    assert iiif.suffix == ".png"


def test_settings_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami import settings as mod

    path = tmp_path / "settings.json"
    monkeypatch.setattr(mod, "_SETTINGS_PATH", path)
    mod.save_settings(mod.ModuleSettings(download_dir="C:/tmp", iiif_workers=12, search_limit=15, force_png=True))
    loaded = mod.load_settings()
    assert loaded.download_dir == "C:/tmp"
    assert loaded.iiif_workers == 12
    assert loaded.search_limit == 15
    assert loaded.force_png is True


def test_visual_hash_identical() -> None:
    from io import BytesIO

    from PIL import Image

    from Komponenty.stronyzobrazami.search.visual_hash import dhash, similarity_score

    buf = BytesIO()
    Image.new("RGB", (64, 64), color=(120, 80, 40)).save(buf, format="PNG")
    raw = buf.getvalue()
    h1 = dhash(raw)
    h2 = dhash(raw)
    assert similarity_score(h1, h2) == 100.0


def test_parse_title_hint() -> None:
    from Komponenty.stronyzobrazami.search.image_search import _parse_title_hint

    title, artist = _parse_title_hint("Starry Night — Vincent van Gogh")
    assert "Starry" in title
    assert "Gogh" in artist


def test_link_matches_sources() -> None:
    from Komponenty.stronyzobrazami.search.image_search import _link_matches_sources
    from Komponenty.stronyzobrazami.search.registry import get_source
    from Komponenty.stronyzobrazami.search.reverse_urls import ReverseLink

    met = get_source("met")
    assert met is not None
    link = ReverseLink(url="https://www.metmuseum.org/art/collection/search/12345/objects/123456")
    assert _link_matches_sources(link, [met]) is True
    rijks = get_source("rijks")
    assert rijks is not None
    assert _link_matches_sources(link, [rijks]) is False


def test_lookup_met_url(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.url_lookup import lookup_hit_from_url

    def fake_json(url, **kwargs):
        if "/objects/123" in url or url.endswith("/436105"):
            return {
                "title": "Test Work",
                "artistDisplayName": "Artist",
                "objectURL": "https://www.metmuseum.org/art/collection/search/1/123",
                "primaryImageSmall": "https://images.metmuseum.org/x.jpg",
            }
        raise RuntimeError(url)

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.url_lookup.get_json",
        fake_json,
    )
    hit = lookup_hit_from_url("https://www.metmuseum.org/art/collection/search/494/436105")
    assert hit is not None
    assert hit.title == "Test Work"
    assert hit.source_id == "met"
