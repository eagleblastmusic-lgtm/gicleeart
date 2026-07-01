"""Testy silnika wyszukiwania stronyzobrazami."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_source_for_url_met() -> None:
    from Komponenty.stronyzobrazami.search.registry import source_for_url

    src = source_for_url("https://www.metmuseum.org/art/collection")
    assert src is not None
    assert src.source_id == "met"


def test_sources_for_sites_dedupes_mia() -> None:
    from Komponenty.stronyzobrazami.search.registry import sources_for_sites
    from Komponenty.stronyzobrazami.storage import SiteEntry

    sites = [
        SiteEntry(id="1", title="Mia A", url="https://collections.artsmia.org/search/", category="Muzeum"),
        SiteEntry(id="2", title="Mia B", url="https://collections.artsmia.org/search/rights", category="Muzeum"),
        SiteEntry(id="3", title="Met", url="https://www.metmuseum.org/art/collection", category="Muzeum"),
    ]
    srcs = sources_for_sites(sites)
    ids = [s.source_id for s in srcs]
    assert ids.count("mia") == 1
    assert "met" in ids


def test_web_fallback_hit() -> None:
    from Komponenty.stronyzobrazami.search.web_urls import web_fallback_hits

    hits = web_fallback_hits("belvedere", "Belvedere", artist="Gustav Klimt", title="The Kiss")
    assert len(hits) == 1
    assert hits[0].search_mode == "web"
    assert "sammlung.belvedere.at" in hits[0].object_url


def test_search_collections_uses_selected_sources(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters
    from Komponenty.stronyzobrazami.search.engine import search_collections
    from Komponenty.stronyzobrazami.search.registry import SourceDef
    from Komponenty.stronyzobrazami.storage import SiteEntry

    def fake_met(**kwargs):
        from Komponenty.stronyzobrazami.search.types import ArtworkHit

        return [
            ArtworkHit(
                source_id="met",
                source_name="The Met",
                title="Test Painting",
                artist=kwargs.get("artist", ""),
                object_url="https://example.org/1",
            ),
        ]

    monkeypatch.setitem(adapters._API_SEARCH, "met", fake_met)

    sites = [
        SiteEntry(id="1", title="Met", url="https://www.metmuseum.org/art/collection", category="Muzeum"),
    ]
    agg = search_collections(artist="Monet", title="", sites=sites, source_ids=["met"], limit_per_source=3)
    assert agg.total_hits == 1
    assert agg.all_hits[0].title == "Test Painting"


def test_smithsonian_key_hint(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import env_keys as mod

    monkeypatch.setattr(mod, "smithsonian_api_key", lambda: "")
    assert mod.smithsonian_api_key_hint() == ""
    monkeypatch.setattr(mod, "smithsonian_api_key", lambda: "abcdefghijklmnop")
    assert mod.smithsonian_api_key_hint() == "...klmnop"


def test_set_smithsonian_api_key(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import env_keys as mod
    from Komponenty.limity import env_config

    env_file = tmp_path / ".env"
    monkeypatch.setattr(env_config, "_env_path", lambda: env_file)

    path = mod.set_smithsonian_api_key("test-key-12345678")
    assert path == env_file
    assert "SMITHSONIAN_API_KEY=test-key-12345678" in env_file.read_text(encoding="utf-8")
    assert mod.smithsonian_api_key() == "test-key-12345678"


def test_format_source_error() -> None:
    from Komponenty.stronyzobrazami.search.errors import format_source_error

    msg = format_source_error("HTTP 429: too many", source_name="The Met")
    assert "429" in msg
    assert "Met" in msg

    msg2 = format_source_error("Brak SMITHSONIAN_API_KEY", source_name="Smithsonian")
    assert "klucz" in msg2.lower()


def test_source_for_url_rijks_api() -> None:
    from Komponenty.stronyzobrazami.search.registry import source_for_url

    src = source_for_url("https://www.rijksmuseum.nl/en")
    assert src is not None
    assert src.source_id == "rijks"
    assert src.api is True


def test_search_rijks_parses_lod(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    sample_obj = {
        "id": "https://id.rijksmuseum.nl/99",
        "identified_by": [
            {
                "type": "Name",
                "content": "The Night Watch",
                "classified_as": [{"id": "http://vocab.getty.edu/aat/300417207"}],
                "language": [{"id": "http://vocab.getty.edu/aat/300388277"}],
            },
        ],
        "produced_by": {
            "timespan": {"identified_by": [{"content": "1642"}]},
            "referred_to_by": [
                {
                    "content": "Rembrandt van Rijn",
                    "classified_as": [{"id": "http://vocab.getty.edu/aat/300435416"}],
                    "language": [{"id": "http://vocab.getty.edu/aat/300388277"}],
                },
            ],
        },
        "subject_of": [
            {
                "digitally_carried_by": [
                    {
                        "access_point": [
                            {"id": "https://www.rijksmuseum.nl/en/collection/object/SK-C-5"},
                        ],
                    },
                ],
            },
        ],
        "shows": [{"id": "https://id.rijksmuseum.nl/202"}],
    }

    def fake_get_json(url, **kwargs):
        if "search/collection" in url:
            return {"orderedItems": [{"id": "https://id.rijksmuseum.nl/99"}]}
        if url.endswith("/99"):
            return sample_obj
        if url.endswith("/202"):
            return {
                "digitally_shown_by": [
                    {"id": "https://id.rijksmuseum.nl/500"},
                ],
            }
        if url.endswith("/500"):
            return {
                "access_point": [
                    {"id": "https://iiif.example/full/max/0/default.jpg"},
                ],
            }
        raise AssertionError(url)

    monkeypatch.setattr(adapters, "get_json", fake_get_json)
    from Komponenty.stronyzobrazami.search import rijks_lod

    monkeypatch.setattr(rijks_lod, "get_json", fake_get_json)
    hits = adapters.search_rijks(artist="Rembrandt", title="Night", limit=3)
    assert len(hits) == 1
    assert hits[0].title == "The Night Watch"
    assert "180," in hits[0].image_url


def test_search_collections_cancel(monkeypatch) -> None:
    import threading

    from Komponenty.stronyzobrazami.search import adapters
    from Komponenty.stronyzobrazami.search.engine import search_collections
    from Komponenty.stronyzobrazami.storage import SiteEntry

    cancel = threading.Event()

    def slow_met(**kwargs):
        cancel.set()
        from Komponenty.stronyzobrazami.search.types import ArtworkHit

        return [
            ArtworkHit(
                source_id="met",
                source_name="The Met",
                title="X",
                object_url="https://example.org",
            ),
        ]

    monkeypatch.setitem(adapters._API_SEARCH, "met", slow_met)

    sites = [
        SiteEntry(id="1", title="Met", url="https://www.metmuseum.org/art/collection", category="Muzeum"),
        SiteEntry(id="2", title="Rijks", url="https://www.rijksmuseum.nl/en", category="Muzeum"),
    ]
    agg = search_collections(
        artist="Test",
        title="",
        sites=sites,
        source_ids=["met", "rijks"],
        cancel_event=cancel,
    )
    assert agg.cancelled is True


def test_is_sculpture_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_sculpture_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    assert is_sculpture_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Bust of Caesar",
            object_type="Sculpture",
        ),
    )
    assert not is_sculpture_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Sunflowers",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )
    assert not is_sculpture_hit(
        ArtworkHit(
            source_id="getty",
            source_name="Getty",
            title="Search",
            search_mode="web",
            object_type="Sculpture",
        ),
    )


def test_is_drawing_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_drawing_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    assert is_drawing_hit(
        ArtworkHit(
            source_id="nga",
            source_name="NGA",
            title="Study",
            object_type="Drawing",
            medium="graphite on paper",
        ),
    )
    assert is_drawing_hit(
        ArtworkHit(
            source_id="artic",
            source_name="Artic",
            title="Plan",
            object_type="Architectural Drawing",
            medium="Ink on paper",
        ),
    )
    assert not is_drawing_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Sunflowers",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )
    assert not is_drawing_hit(
        ArtworkHit(
            source_id="walters",
            source_name="Walters",
            title="Portrait",
            object_type="Painting & Drawing",
            medium="oil on canvas",
        ),
    )


def test_is_print_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_print_hit, should_skip_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    mia_mezzotint = ArtworkHit(
        source_id="mia",
        source_name="Mia",
        title="Hadleigh Castle, near the Nore",
        artist="John Constable; David Lucas",
        object_type="Prints",
        medium="Mezzotint",
        object_url="https://collections.artsmia.org/art/43767",
        search_mode="api",
    )
    assert is_print_hit(mia_mezzotint)
    assert should_skip_hit(mia_mezzotint)

    assert not is_print_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Sunflowers",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )
    assert not is_print_hit(
        ArtworkHit(
            source_id="getty",
            source_name="Getty",
            title="Search",
            search_mode="web",
            object_type="Print",
        ),
    )


def test_is_album_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_album_hit, should_skip_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    westmorland = ArtworkHit(
        source_id="getty",
        source_name="Getty",
        title="[The Westmorland album]",
        artist="John Jabez Edwin Mayall",
        object_type="Album",
        object_url="https://www.getty.edu/art/collection/object/1040P3",
        search_mode="api",
    )
    assert is_album_hit(westmorland)
    assert should_skip_hit(westmorland)

    assert not is_album_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Sunflowers",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )

    smithsonian_folder = ArtworkHit(
        source_id="smithsonian",
        source_name="Smithsonian",
        title="John Constable, 1776-1837 [Folder]",
        artist="Constable, John",
        object_url="https://www.si.edu/object/id:example",
        search_mode="api",
    )
    assert is_album_hit(smithsonian_folder)
    assert should_skip_hit(smithsonian_folder)


def test_is_archaeological_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_archaeological_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    assert is_archaeological_hit(
        ArtworkHit(
            source_id="walters",
            source_name="Walters",
            title="Greek Vase",
            object_type="Ceramics",
            medium="terracotta",
        ),
    )
    assert is_archaeological_hit(
        ArtworkHit(
            source_id="cleveland",
            source_name="Cleveland",
            title="Granodiorite deity",
            object_type="Sculpture",
            department="Egyptian and Ancient Near Eastern Art",
            medium="granodiorite",
        ),
    )
    assert is_archaeological_hit(
        ArtworkHit(
            source_id="nga",
            source_name="NGA",
            title="Bowl",
            object_type="Decorative Art",
        ),
    )
    assert not is_archaeological_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Landscape",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )


def test_is_publication_hit() -> None:
    from Komponenty.stronyzobrazami.search.filters import is_album_hit, is_publication_hit
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    assert is_publication_hit(
        ArtworkHit(
            source_id="smithsonian",
            source_name="Smithsonian",
            title="Monet and his muse : Camille Monet in the artist's life",
            object_type="Books",
            object_url="https://siris-libraries.si.edu/ipac20/ipac.jsp?profile=liball",
        ),
    )
    assert is_publication_hit(
        ArtworkHit(
            source_id="smithsonian",
            source_name="Smithsonian",
            title="Muse heute?",
            object_type="Exhibitions (events)",
            object_url="https://siris-libraries.si.edu/ipac20/ipac.jsp",
        ),
    )
    assert not is_publication_hit(
        ArtworkHit(
            source_id="met",
            source_name="Met",
            title="Water Lilies",
            object_type="Paintings",
            medium="Oil on canvas",
        ),
    )
    assert not is_publication_hit(
        ArtworkHit(
            source_id="nga",
            source_name="NGA",
            title="Series of prints",
            object_type="Portfolio",
        ),
    )
    assert is_album_hit(
        ArtworkHit(
            source_id="nga",
            source_name="NGA",
            title="Series of prints",
            object_type="Portfolio",
        ),
    )


def test_artic_preview_url_and_headers() -> None:
    from Komponenty.stronyzobrazami.search.artic_images import (
        artic_fetch_headers,
        artic_preview_url,
    )

    uid = "3c27b499-af56-f0d5-93b5-a7f2f1ad5813"
    assert artic_preview_url(uid).endswith("/full/200,/0/default.jpg")
    assert artic_fetch_headers()["Referer"] == "https://www.artic.edu/"
    assert "16568" in artic_fetch_headers(artwork_id=16568)["Referer"]


def test_artic_fetch_with_referer() -> None:
    import urllib.request

    from Komponenty.stronyzobrazami.search.artic_images import artic_fetch_headers, artic_preview_url
    from Komponenty.stronyzobrazami.search.thumbnails import fetch_thumbnail_bytes

    url = artic_preview_url("3c27b499-af56-f0d5-93b5-a7f2f1ad5813")
    raw = fetch_thumbnail_bytes(url, timeout=20)
    assert raw and raw[:2] == b"\xff\xd8"

    req = urllib.request.Request(url, headers={"User-Agent": "test", **artic_fetch_headers()})
    with urllib.request.urlopen(req, timeout=20) as resp:
        assert resp.read(2) == b"\xff\xd8"


def test_mia_preview_url() -> None:
    from Komponenty.stronyzobrazami.search.mia_images import mia_preview_url, normalize_mia_image_url

    assert mia_preview_url(10436) == "https://6.api.artsmia.org/10436.jpg"
    assert mia_preview_url(10436, large=True) == "https://6.api.artsmia.org/800/10436.jpg"
    assert normalize_mia_image_url(
        "https://api.artsmia.org/images/10436/small.jpg",
    ) == "https://6.api.artsmia.org/10436.jpg"


def test_cleveland_image_url_prefers_print() -> None:
    from Komponenty.stronyzobrazami.search.adapters import _cleveland_image_url

    url = _cleveland_image_url(
        {
            "web": {"url": "https://openaccess-cdn.clevelandart.org/web/small.jpg"},
            "print": {"url": "https://openaccess-cdn.clevelandart.org/print/large.jpg"},
        },
    )
    assert url.endswith("print/large.jpg")


def test_getty_preview_url_from_manifest() -> None:
    from Komponenty.stronyzobrazami.search.adapters import _getty_preview_url

    url = _getty_preview_url(
        {"thumb": "https://media.getty.edu/iiif/image/x/full/!300,300/0/default.jpg"},
    )
    assert "/full/800,/" in url


def test_smithsonian_object_and_image_url(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search.smithsonian_media import (
        smithsonian_image_url,
        smithsonian_object_url,
    )

    row = {
        "id": "SAAM_123",
        "content": {
            "descriptiveNonRepeating": {
                "record_link": {"content": "https://americanart.si.edu/artwork/example"},
            },
        },
    }
    assert smithsonian_object_url(row) == "https://americanart.si.edu/artwork/example"

    def fake_get_json(url, **kwargs):
        assert "onlineMedia" in url
        return {
            "response": {
                "rows": [
                    {
                        "content": {
                            "descriptiveNonRepeating": {
                                "online_media": {
                                    "media": [
                                        {
                                            "content": "https://ids.si.edu/ids/deliveryService?id=SAAM-123",
                                        },
                                    ],
                                },
                            },
                        },
                    },
                ],
            },
        }

    monkeypatch.setattr(
        "Komponenty.stronyzobrazami.search.smithsonian_media.get_json",
        fake_get_json,
    )
    img = smithsonian_image_url("SAAM_123", api_key="test-key-12345678", large=True)
    assert "deliveryService" in img
    assert "&max=0" in img


def test_optimize_preview_url() -> None:
    from Komponenty.stronyzobrazami.search.thumbnails import optimize_preview_url

    assert "200," in optimize_preview_url(
        "https://www.artic.edu/iiif/2/x/full/843,/0/default.jpg",
    )
    assert optimize_preview_url(
        "https://api.artsmia.org/images/123/medium.jpg",
    ).endswith("/123.jpg")
    assert "6.api.artsmia.org" in optimize_preview_url(
        "https://api.artsmia.org/images/10436/small.jpg",
    )
    nf = optimize_preview_url(
        "https://iiif.discovernewfields.org/iiif/3/4285-7a2b507cd2af10b8__small",
    )
    assert nf.endswith("/0/default.jpg")
    assert "!200,200" in nf
    assert "__small" not in nf


def test_load_nga_constituent_display_names(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import local_data as mod

    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_ensure_file", lambda _url, dest: dest)
    mod._nga_rows = None
    mod._nga_artist_by_object = None
    mod._nga_by_oid = None
    mod._nga_artist_index = None
    mod._nga_people_qid = None

    (tmp_path / "nga_constituents.csv").write_text(
        "constituentid,forwarddisplayname,preferreddisplayname\n"
        "1726,Claude Monet,\"Monet, Claude\"\n",
        encoding="utf-8",
    )
    (tmp_path / "nga_objects_constituents.csv").write_text(
        "objectid,constituentid,role\n45872,1726,artist\n",
        encoding="utf-8",
    )
    (tmp_path / "nga_objects.csv").write_text(
        "objectid,title,attribution,classification,displaydate,medium,accessionnum\n"
        "45872,Morning Haze,Claude Monet,Painting,1872,oil on canvas,1958.1.1\n",
        encoding="utf-8",
    )

    _rows, artist_map = mod._load_nga()
    assert artist_map["45872"] == ["Claude Monet"]

    mod._nga_rows = None
    mod._nga_artist_by_object = None
    mod._nga_by_oid = None
    mod._nga_artist_index = None
    mod._nga_people_qid = None


def test_search_nga_artist_match(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import local_data as mod

    rows = [
        {
            "objectid": "45872",
            "title": "Morning Haze",
            "attribution": "Claude Monet",
            "classification": "Painting",
            "displaydate": "1872",
            "medium": "oil on canvas",
            "accessionnum": "1958.1.1",
        },
        {
            "objectid": "2045",
            "title": "Jupiter prend la forme de Diane",
            "attribution": "Jean-Baptiste Blaise Simonet after Charles Eisen",
            "classification": "Print",
            "displaydate": "1767",
            "medium": "etching",
            "accessionnum": "1942.9.884",
        },
    ]
    artist_map = {"45872": ["Claude Monet"]}
    monkeypatch.setattr(mod, "_load_nga", lambda: (rows, artist_map))
    monkeypatch.setattr(mod, "_nga_row_iter", lambda **kwargs: rows if not kwargs.get("artist") else [rows[0]])

    hits = mod.search_nga(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].title == "Morning Haze"
    assert hits[0].artist == "Claude Monet"
    assert hits[0].search_mode == "local"

    monkeypatch.setattr(mod, "_load_nga", lambda: (rows, {}))
    monkeypatch.setattr(mod, "_nga_row_iter", lambda **kwargs: rows)
    hits_attr = mod.search_nga(artist="Monet", title="", limit=5)
    assert len(hits_attr) == 1
    assert hits_attr[0].artist == "Claude Monet"


def test_artist_match_requires_all_tokens() -> None:
    from Komponenty.stronyzobrazami.search.local_data import _artist_match

    assert _artist_match("Albert Bierstadt", "Albert Bierstadt")
    assert _artist_match("Albert Bierstadt", "Bierstadt, Albert")
    assert not _artist_match("Albert Bierstadt", "Albert Besnard")
    assert not _artist_match("Albert Bierstadt", "Albert, Prince")


def test_artist_match_diacritics() -> None:
    from Komponenty.stronyzobrazami.search.artist_match import artist_match

    assert artist_match("Albrecht Durer", "Albrecht D\u00fcrer", fetch_wikidata=False)
    assert artist_match("Albrecht D\u00fcrer", "Albrecht Durer", fetch_wikidata=False)
    assert artist_match("Rene Magritte", "Ren\u00e9 Magritte", fetch_wikidata=False)
    assert not artist_match("Albrecht Durer", "Albrecht Muller", fetch_wikidata=False)


def test_artist_match_transliteration() -> None:
    from Komponenty.stronyzobrazami.search.artist_match import artist_match

    assert artist_match("\u0420\u0435\u043f\u0438\u043d", "Ilya Repin", fetch_wikidata=False)
    assert artist_match("Repin", "Ilya Repin", fetch_wikidata=False)
    assert not artist_match("\u0420\u0435\u043f\u0438\u043d", "Albert Besnard", fetch_wikidata=False)


def test_artist_match_fuzzy_first_name() -> None:
    from Komponenty.stronyzobrazami.search.artist_match import artist_match

    assert artist_match("Johann Vermeer", "Johannes Vermeer", fetch_wikidata=False)
    assert not artist_match("Johann Vermeer", "Jan Steen", fetch_wikidata=False)


def test_artist_match_wikidata_aliases(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import wikidata_artists as wd
    from Komponenty.stronyzobrazami.search.artist_match import artist_match

    wd.reset_cache_for_tests()
    monkeypatch.setattr(
        wd,
        "labels_for_query",
        lambda query, fetch=True: [
            "Albrecht D\u00fcrer",
            "Albrecht Durer",
        ]
        if "durero" in query.lower() or "durer" in query.lower()
        else [],
    )
    assert artist_match("Albrecht Durero", "Albrecht D\u00fcrer", fetch_wikidata=True)


def test_search_nga_bierstadt_not_besnard(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import local_data as mod

    rows = [
        {
            "objectid": "166428",
            "title": "Mount Corcoran",
            "attribution": "Albert Bierstadt",
            "classification": "Painting",
            "displaydate": "c. 1876-1877",
            "medium": "oil on canvas",
            "accessionnum": "2014.79.4",
        },
        {
            "objectid": "999",
            "title": "Some Etching",
            "attribution": "Albert Besnard",
            "classification": "Print",
            "displaydate": "1889",
            "medium": "etching",
            "accessionnum": "X.1",
        },
    ]
    artist_map = {
        "166428": ["Albert Bierstadt"],
        "999": ["Albert Besnard"],
    }
    monkeypatch.setattr(mod, "_load_nga", lambda: (rows, artist_map))

    def _filtered(**kwargs):
        artist = kwargs.get("artist", "")
        out = []
        for row in rows:
            oid = row["objectid"]
            artists = ", ".join(artist_map.get(oid, []))
            if mod._artist_match(artist, artists):
                out.append(row)
        return out

    monkeypatch.setattr(mod, "_nga_row_iter", _filtered)
    hits = mod.search_nga(artist="Albert Bierstadt", title="", limit=10)
    assert len(hits) == 1
    assert hits[0].title == "Mount Corcoran"
    assert hits[0].raw_id == "166428"


def test_search_nga_mount_corcoran_in_cache() -> None:
    from Komponenty.stronyzobrazami.search import local_data as mod

    mod._nga_rows = None
    mod._nga_artist_by_object = None
    mod._nga_by_oid = None
    mod._nga_artist_index = None
    mod._nga_people_qid = None

    hits = mod.search_nga(artist="Albert Bierstadt", title="Mount Corcoran", limit=5)
    assert any(h.raw_id == "166428" for h in hits)
    assert any("Mount Corcoran" in h.title for h in hits)


def test_search_source_local_empty_not_web_fallback(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters
    from Komponenty.stronyzobrazami.search.registry import SourceDef

    src = SourceDef(
        source_id="nga",
        name="National Gallery of Art",
        patterns=(r"nga\.gov",),
        local=True,
        web_fallback=True,
    )

    monkeypatch.setitem(adapters._LOCAL_SEARCH, "nga", lambda **kwargs: [])
    hits, err, mode = adapters.search_source(src, artist="Monet", title="", limit=5)
    assert hits == []
    assert mode == "local"
    assert err == ""


def test_search_getty_excludes_drawings(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    calls: list[str] = []

    def fake_get_json(url, **kwargs):
        calls.append(url)
        if "size=1" in url:
            return {
                "facets": {
                    "classification_and_object_type": [
                        {"name": "Painting", "val": 2},
                        {"name": "Drawing", "val": 1},
                    ],
                },
            }
        return {
            "data": [
                {
                    "id": "object/paint-1",
                    "primary_name": "The Portal of Rouen Cathedral in Morning Light",
                    "producers": [
                        {
                            "primary_name": "Claude Monet",
                            "all_names": ["Monet, Claude", "Claude Monet"],
                            "role": ["Artist"],
                        },
                    ],
                    "date_created": "1894",
                    "accession_number": "2001.33",
                    "slug_with_path": "/object/108HGY",
                    "manifest": {"thumb": "https://media.getty.edu/iiif/image/x/full/!300,300/0/default.jpg"},
                    "is_parent": False,
                    "is_standalone": True,
                },
            ],
        }

    monkeypatch.setattr(adapters, "get_json", fake_get_json)
    hits = adapters.search_getty(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].search_mode == "api"
    assert hits[0].title.startswith("The Portal of Rouen")
    assert "Drawing" not in calls[1]
    assert "Album" not in calls[1]
    assert "classification_and_object_type=Painting" in calls[1]


def test_search_getty_skips_album_parent(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    def fake_get_json(url, **kwargs):
        if "size=1" in url:
            return {
                "facets": {
                    "classification_and_object_type": [
                        {"name": "Painting", "val": 1},
                        {"name": "Album", "val": 1},
                    ],
                },
            }
        return {
            "data": [
                {
                    "id": "object/album-1",
                    "primary_name": "[The Westmorland album]",
                    "is_parent": True,
                    "is_standalone": True,
                    "producers": [{"primary_name": "John Constable", "role": ["Artist"]}],
                    "date_created": "1859",
                    "slug_with_path": "/object/1040P3",
                    "manifest": {"thumb": "https://media.getty.edu/iiif/image/x/full/!300,300/0/default.jpg"},
                },
                {
                    "id": "object/paint-1",
                    "primary_name": "Hadleigh Castle",
                    "is_parent": False,
                    "is_standalone": True,
                    "producers": [{"primary_name": "John Constable", "role": ["Artist"]}],
                    "date_created": "1829",
                    "slug_with_path": "/object/abc",
                    "manifest": {"thumb": "https://media.getty.edu/iiif/image/y/full/!300,300/0/default.jpg"},
                },
            ],
        }

    monkeypatch.setattr(adapters, "get_json", fake_get_json)
    hits = adapters.search_getty(artist="Constable", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].title == "Hadleigh Castle"


def test_search_source_getty_api_not_web(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters
    from Komponenty.stronyzobrazami.search.registry import SourceDef
    from Komponenty.stronyzobrazami.search.types import ArtworkHit

    src = SourceDef(
        source_id="getty",
        name="Getty Museum",
        patterns=(r"getty\.edu",),
        web_fallback=True,
    )

    def fake_getty(**kwargs):
        return [
            ArtworkHit(
                source_id="getty",
                source_name="Getty Museum",
                title="Morning Light",
                artist="Claude Monet",
                object_url="https://www.getty.edu/art/collection/object/108HGY",
                search_mode="api",
            ),
        ]

    monkeypatch.setitem(adapters._API_SEARCH, "getty", fake_getty)
    hits, err, mode = adapters.search_source(src, artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert mode == "api"
    assert err == ""
    assert hits[0].search_mode == "api"


def test_parse_belvedere_manifest() -> None:
    from Komponenty.stronyzobrazami.search.belvedere_iiif import parse_belvedere_manifest

    manifest = {
        "label": "Weg in Monets Garten in Giverny",
        "@id": "https://sammlung.belvedere.at/apis/iiif/presentation/v2/1-objects-2683/manifest",
        "related": [
            {
                "@id": "https://sammlung.belvedere.at/objects/2683/eine-allee-in-monets-garten-in-giverny",
            },
        ],
        "sequences": [
            {
                "canvases": [
                    {
                        "label": (
                            "Claude Monet, Eine Allee in Monets Garten in Giverny, 1902, "
                            "Öl auf Leinwand, 89,5 x 92,3 cm, Belvedere, Wien, Inv.-Nr. 3889"
                        ),
                        "images": [
                            {
                                "resource": {
                                    "service": {
                                        "@id": "https://sammlung.belvedere.at/apis/iiif/image/v2/70888",
                                    },
                                },
                            },
                        ],
                    },
                ],
            },
        ],
    }
    parsed = parse_belvedere_manifest(manifest)
    assert parsed["title"] == "Weg in Monets Garten in Giverny"
    assert parsed["artist"] == "Claude Monet"
    assert parsed["object_type"] == "Painting"
    assert parsed["raw_id"] == "2683"
    assert parsed["image_url"].endswith("/full/!300,300/0/default.jpg")


def test_search_belvedere_monet(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    manifest = {
        "label": "Weg in Monets Garten in Giverny",
        "@id": "https://sammlung.belvedere.at/apis/iiif/presentation/v2/1-objects-2683/manifest",
        "related": [
            {"@id": "https://sammlung.belvedere.at/objects/2683/eine-allee-in-monets-garten-in-giverny"},
        ],
        "sequences": [
            {
                "canvases": [
                    {
                        "label": (
                            "Claude Monet, Eine Allee in Monets Garten in Giverny, 1902, "
                            "Öl auf Leinwand, 89,5 x 92,3 cm, Belvedere, Wien, Inv.-Nr. 3889"
                        ),
                        "images": [
                            {
                                "resource": {
                                    "service": {
                                        "@id": "https://sammlung.belvedere.at/apis/iiif/image/v2/70888",
                                    },
                                },
                            },
                        ],
                    },
                ],
            },
        ],
    }

    def fake_get_json(url, **kwargs):
        if url.endswith("/objects/Monet"):
            return {
                "collections": [
                    {
                        "@id": "https://sammlung.belvedere.at/apis/iiif/presentation/v2/collection/search/objects/Monet?page=1",
                    },
                ],
            }
        if url.endswith("Monet?page=1"):
            return {
                "manifests": [
                    {"@id": "https://sammlung.belvedere.at/apis/iiif/presentation/v2/1-objects-2683/manifest"},
                ],
            }
        if url.endswith("1-objects-2683/manifest"):
            return manifest
        raise AssertionError(url)

    monkeypatch.setattr(adapters, "get_json", fake_get_json)
    hits = adapters.search_belvedere(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].search_mode == "api"
    assert hits[0].artist == "Claude Monet"
    assert "/en/objects/2683/" in hits[0].object_url


def test_artist_in_text_word_boundary() -> None:
    from Komponenty.stronyzobrazami.search.adapters import _artist_in_text

    assert _artist_in_text("Monet", "Claude Monet")
    assert not _artist_in_text("Monet", "Nicola Moneta")
    assert not _artist_in_text("Monet", "Jean-Baptiste Simonet")
    assert _artist_in_text("Albert Bierstadt", "Albert Bierstadt")
    assert not _artist_in_text("Albert Bierstadt", "Albert Besnard")


def test_search_newfields_monet(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    pages = {
        0: {
            "results": [
                {
                    "__typename": "ArchiveCollectionItem",
                    "title": "Monet frame receipt",
                    "creators": [],
                },
                {
                    "__typename": "Artwork",
                    "artwork_id": "53415",
                    "accession_number": "65.15",
                    "title": "Charing Cross Bridge",
                    "date_created_earliest": 1890,
                    "date_created_latest": 1910,
                    "creators": [{"party": {"full_name": "Claude Monet"}}],
                    "images": [
                        {
                            "iiif_thumbnail_url": "https://iiif.discovernewfields.org/iiif/3/53415-x__small",
                        },
                    ],
                },
                {
                    "__typename": "Artwork",
                    "artwork_id": "73423",
                    "accession_number": "37.101",
                    "title": "Supper at Emmaus",
                    "date_created_earliest": 1868,
                    "date_created_latest": 1868,
                    "creators": [{"party": {"full_name": "Nicola Moneta"}}],
                    "images": [],
                },
            ],
        },
    }

    def fake_post_json(url, payload, **kwargs):
        assert payload["searchTerm"] == "Monet"
        return pages[int(payload.get("from", 0))]

    monkeypatch.setattr(adapters, "post_json", fake_post_json)
    hits = adapters.search_newfields(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].title == "Charing Cross Bridge"


def test_search_newfields_filters_mezzotint(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    pages = {
        0: {
            "results": [
                {
                    "__typename": "Artwork",
                    "artwork_id": "72702",
                    "accession_number": "16.1129",
                    "title": "Jaques and the Wounded Stag, from Shakespeare's \"As You Like It\"",
                    "date_created_earliest": 1830,
                    "date_created_latest": 1830,
                    "creators": [
                        {"party": {"full_name": "John Constable"}},
                        {"party": {"full_name": "David Lucas"}},
                    ],
                    "images": [{"iiif_thumbnail_url": "https://iiif.discovernewfields.org/iiif/3/72702-x__small"}],
                },
                {
                    "__typename": "Artwork",
                    "artwork_id": "53415",
                    "accession_number": "65.15",
                    "title": "Charing Cross Bridge",
                    "date_created_earliest": 1890,
                    "date_created_latest": 1910,
                    "creators": [{"party": {"full_name": "Claude Monet"}}],
                    "images": [{"iiif_thumbnail_url": "https://iiif.discovernewfields.org/iiif/3/53415-x__small"}],
                },
            ],
        },
    }

    def fake_post_json(url, payload, **kwargs):
        return pages[int(payload.get("from", 0))]

    def fake_meta(artwork_id, **kwargs):
        if artwork_id == "72702":
            return "prints, engravings, mezzotints", "ink on paper, mezzotint"
        return "paintings", "oil on canvas"

    monkeypatch.setattr(adapters, "post_json", fake_post_json)
    monkeypatch.setattr(adapters, "newfields_artwork_meta", fake_meta)
    hits = adapters.search_newfields(artist="John Constable", title="", limit=5)
    assert len(hits) == 0

    hits_monet = adapters.search_newfields(artist="Monet", title="", limit=5)
    assert len(hits_monet) == 1
    assert hits_monet[0].raw_id == "53415"


def test_registry_new_museums() -> None:
    from Komponenty.stronyzobrazami.search.registry import source_for_url

    cases = (
        ("https://www.parismuseescollections.paris.fr/", "paris_musees"),
        ("https://www.kansallisgalleria.fi/en/search", "fng"),
        ("https://collection.nationalmuseum.se/en", "nationalmuseum_se"),
        ("https://www.mauritshuis.nl/en/", "mauritshuis"),
        ("https://dma.org/art/collection", "dma"),
        ("https://collections.lacma.org/", "lacma"),
        ("https://artmuseum.princeton.edu/collections", "princeton"),
        ("https://www.clarkart.edu/artpiece", "clark"),
        ("https://collection.barnesfoundation.org/", "barnes"),
        ("https://www.slam.org/collection/", "slam"),
        ("https://sammlung.staedelmuseum.de/en", "staedel"),
        ("https://www.mkg-hamburg.de/en/collection", "mkg"),
        ("https://download.kunstmuseumbasel.ch/", "basel"),
        ("https://sammlungenonline.albertina.at/", "albertina"),
        ("https://digitalarchive.npm.gov.tw/", "npm_tw"),
        ("https://zbiory.mnk.pl/", "mnk"),
        ("https://artgallery.yale.edu/collections", "yale_gallery"),
        ("https://philamuseum.org/collection", "philadelphia"),
    )
    for url, expected in cases:
        src = source_for_url(url)
        assert src is not None, url
        assert src.source_id == expected, url


def test_web_urls_new_museums() -> None:
    from Komponenty.stronyzobrazami.search.web_urls import build_web_search_url

    for source_id in (
        "paris_musees",
        "fng",
        "nationalmuseum_se",
        "mauritshuis",
        "dma",
        "lacma",
        "princeton",
        "clark",
        "barnes",
        "slam",
        "staedel",
        "mkg",
        "basel",
        "albertina",
        "npm_tw",
        "mnk",
        "yale_gallery",
        "philadelphia",
    ):
        url = build_web_search_url(source_id, artist="Monet", title="")
        assert url.startswith("https://"), source_id
        assert "Monet" in url, source_id


def test_registry_batch2_museums() -> None:
    from Komponenty.stronyzobrazami.search.registry import source_for_url

    cases = (
        ("https://risdmuseum.org/art-design/collection", "risd"),
        ("https://dia.org/collection", "dia"),
        ("https://www.artsbma.org/collection/", "birmingham_moa"),
        ("https://dams.birminghammuseums.org.uk/", "birmingham_trust"),
        ("https://collections.rammuseum.org.uk/", "ramm"),
        ("https://digitalcollections.nypl.org/", "nypl"),
        ("https://www.loc.gov/collections/", "loc"),
        ("https://wellcomecollection.org/collection", "wellcome"),
        ("https://collections.tepapa.govt.nz/", "tepapa"),
        ("https://collection.cooperhewitt.org/", "cooper_hewitt"),
        ("https://www.europeana.eu/", "europeana"),
        ("https://pdimagearchive.org/", "pdia"),
    )
    for url, expected in cases:
        src = source_for_url(url)
        assert src is not None, url
        assert src.source_id == expected, url


def test_web_urls_batch2_museums() -> None:
    from Komponenty.stronyzobrazami.search.web_urls import build_web_search_url

    for source_id in (
        "risd",
        "dia",
        "birmingham_moa",
        "birmingham_trust",
        "ramm",
        "nypl",
        "loc",
        "wellcome",
        "tepapa",
        "cooper_hewitt",
        "europeana",
        "pdia",
    ):
        url = build_web_search_url(source_id, artist="Millais", title="")
        assert url.startswith("https://"), source_id
        assert "Millais" in url, source_id


def test_loc_api_search(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import loc_api as mod

    def fake_get_json(url, **kwargs):
        return {
            "results": [
                {
                    "title": "John Everett Millais",
                    "url": "https://www.loc.gov/item/92514290/",
                    "contributor": ["Millais, John Everett"],
                    "image_url": ["https://tile.loc.gov/x/150px.jpg", "https://tile.loc.gov/x/1024.jpg"],
                    "date": "1880",
                    "original_format": ["photo, print, drawing"],
                    "id": "92514290",
                },
            ],
        }

    monkeypatch.setattr(mod, "get_json", fake_get_json)
    rows = mod.search_loc(query="John Everett Millais", limit=3)
    assert len(rows) == 1
    assert rows[0]["object_url"].endswith("92514290/")
    assert rows[0]["image_url"].endswith("1024.jpg")


def test_wellcome_api_search(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import wellcome_api as mod

    monkeypatch.setattr(
        mod,
        "get_json",
        lambda url, **kwargs: {
            "results": [
                {
                    "id": "abc123",
                    "title": "Sir John Everett Millais. Photograph.",
                    "thumbnail": {"url": "https://iiif.wellcomecollection.org/image/V0028573/full/300,/0/default.jpg"},
                    "workType": {"label": "Pictures"},
                },
            ],
        },
    )
    rows = mod.search_wellcome(query="Millais", limit=2)
    assert rows[0]["object_url"].endswith("/abc123")
    assert "wellcomecollection.org" in rows[0]["object_url"]


def test_europeana_requires_key(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import europeana_api as mod

    monkeypatch.setattr(mod, "europeana_api_key", lambda: "")
    try:
        mod.search_europeana(query="art", limit=2)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "EUROPEANA_API_KEY" in str(exc)


def test_birmingham_trust_parse_search(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import birmingham_trust_api as mod

    sample_search = """
    <li class="panel js-panel js-add-remove asset">
      <a id="thumbnail-asset-link-3455" href="viewAsset?id=3455">
        <img src="https://d2cbqpmhv5w176.cloudfront.net/thumb.jpg" alt="Waiting scene" />
      </a>
      <ul class="panel__attributes">
        <li>ID: 3455</li>
        <li>1909P62 Waiting</li>
      </ul>
    </li>
    """
    sample_page = "Details of the image asset 1909P62 Waiting | Birmingham Artist: John Everett Millais"

    monkeypatch.setattr(mod, "_get_html", lambda url, **kw: sample_page if "viewAsset" in url else sample_search)
    rows = mod.search_birmingham_trust(query="Millais", limit=3)
    assert len(rows) == 1
    assert rows[0]["raw_id"] == "3455"
    assert rows[0]["artist"] == "John Everett Millais"
    assert "3455" in rows[0]["object_url"]


def test_paris_musees_parse_search_html() -> None:
    from Komponenty.stronyzobrazami.search.paris_musees_api import _parse_search_html

    sample = """
    <article about="/en/node/999001" class="node-oeuvre-search-result">
      <a href="/en/node/999001">
        <img src="https://apicollections.parismusees.paris.fr/sites/default/files/styles/thumbnail/x.jpg" />
        <h3>Ophelia</h3>
      </a>
    </article>
    """
    rows = _parse_search_html(sample, limit=5)
    assert len(rows) == 1
    assert rows[0]["raw_id"] == "999001"
    assert rows[0]["title"] == "Ophelia"
    assert "999001" in rows[0]["object_url"]


def test_paris_musees_graphql_blocked_falls_back_to_html(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import paris_musees_api as mod

    monkeypatch.setattr(mod, "paris_musees_api_token", lambda: "test-token")
    monkeypatch.setattr(
        mod,
        "_search_graphql",
        lambda **kw: (_ for _ in ()).throw(mod.ParisMuseesGraphQLBlocked("403")),
    )
    monkeypatch.setattr(
        mod,
        "_search_web",
        lambda **kw: [{"title": "Fallback", "artist": "", "object_url": "https://x", "image_url": "", "raw_id": "1"}],
    )
    rows = mod.search_paris_musees(query="Millais", limit=3)
    assert len(rows) == 1
    assert rows[0]["title"] == "Fallback"


def test_search_albertina(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import adapters

    def fake_get_json(url, **kwargs):
        if "page=" in url:
            return {"manifests": []}
        if "search/objects/Monet" in url and "manifest" not in url:
            return {
                "manifests": [
                    {"@id": "https://sammlungenonline.albertina.at/apis/iiif/presentation/v2/1-objects-305501/manifest"},
                ],
            }
        if "305501/manifest" in url:
            return {
                "@id": "https://sammlungenonline.albertina.at/apis/iiif/presentation/v2/1-objects-305501/manifest",
                "label": "Blick auf Vétheuil",
                "related": [{"@id": "https://sammlungenonline.albertina.at/objects/305501/blick-auf-vetheuil"}],
                "sequences": [
                    {
                        "canvases": [
                            {
                                "label": "Claude Monet, Blick auf Vétheuil, Inv. Nr.: GE86DL",
                                "images": [
                                    {
                                        "resource": {
                                            "service": {
                                                "@id": "https://sammlungenonline.albertina.at/apis/iiif/image/v2/511793",
                                            },
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        raise AssertionError(url)

    monkeypatch.setattr(adapters, "get_json", fake_get_json)
    hits = adapters.search_albertina(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].source_id == "albertina"
    assert hits[0].title == "Blick auf Vétheuil"
    assert hits[0].artist == "Claude Monet"
    assert hits[0].raw_id == "305501"


def test_parse_iiif_manifest_albertina_label() -> None:
    from Komponenty.stronyzobrazami.search.iiif_presentation_search import parse_canvas_label

    parsed = parse_canvas_label("Claude Monet, Blick auf Vétheuil, Inv. Nr.: GE86DL")
    assert parsed["artist"] == "Claude Monet"
    assert parsed["title"] == "Blick auf Vétheuil"
    assert parsed["accession"] == "GE86DL"


def test_search_fng_local(monkeypatch, tmp_path) -> None:
    import gzip
    import json

    from Komponenty.stronyzobrazami.search import fng_local as mod

    sample = [
        {
            "objectId": 1001,
            "title": {"en": "Water Lilies", "fi": "Lummekukkia"},
            "people": [
                {
                    "firstName": "Claude",
                    "familyName": "Monet",
                    "role": {"fi": "taiteilija"},
                },
            ],
            "multimedia": [{"jpg": {"500": "https://example.com/monet.jpg"}}],
            "timePeriod": {"en": "1900"},
            "technique": {"en": "oil on canvas"},
        },
        {
            "objectId": 1002,
            "title": {"en": "Hay Wain", "fi": "..."},
            "people": [
                {
                    "firstName": "John",
                    "familyName": "Constable",
                    "role": {"fi": "taiteilija"},
                },
            ],
            "multimedia": [{"jpg": {"500": "https://example.com/constable.jpg"}}],
        },
    ]
    cache = tmp_path / "fng_objects.json.gz"
    with gzip.open(cache, "wt", encoding="utf-8") as fh:
        json.dump(sample, fh)

    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(mod, "FNG_OBJECTS_GZ", cache)
    mod.reset_fng_cache_for_tests()

    hits = mod.search_fng_local(artist="Monet", title="", limit=5)
    assert len(hits) == 1
    assert hits[0].title == "Water Lilies"
    assert hits[0].search_mode == "local"


def test_search_fng_api(monkeypatch) -> None:
    from Komponenty.stronyzobrazami.search import fng_api

    def fake_post(url, payload, **kwargs):
        assert "kokoelma.kansallisgalleria.fi" in url
        assert payload == {"searchTerms": ["Monet"], "hasImage": True}
        return [
            {
                "objectId": 621905,
                "title": {"en": "Water Lilies"},
                "people": [
                    {
                        "firstName": "Claude",
                        "familyName": "Monet",
                        "role": {"fi": "taiteilija"},
                    },
                ],
                "multimedia": [{"jpg": {"500": "https://example.com/monet.jpg"}}],
            },
        ]

    monkeypatch.setattr(fng_api, "post_json", fake_post)
    monkeypatch.setattr(fng_api, "fng_api_key", lambda: "test-key")
    rows = fng_api.search_fng_api(artist="Monet", title="", limit=5)
    assert len(rows) == 1
    assert rows[0]["title"] == "Water Lilies"
    assert rows[0]["artist"] == "Claude Monet"
