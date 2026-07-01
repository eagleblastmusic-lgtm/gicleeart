"""Testy modulu stronyzobrazami."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_parse_bulk_links() -> None:
    from Komponenty.stronyzobrazami.storage import parse_bulk_links

    text = """
    https://www.louvre.fr/
    Rijksmuseum | https://www.rijksmuseum.nl/
    # komentarz
    https://www.louvre.fr/
    """
    rows = parse_bulk_links(text)
    assert len(rows) == 2
    assert rows[0][1].startswith("https://www.louvre.fr")
    assert rows[1][0] == "Rijksmuseum"


def test_normalize_url_adds_scheme() -> None:
    from Komponenty.stronyzobrazami.storage import normalize_url

    assert normalize_url("example.com/gallery").startswith("https://")


def test_load_save_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.stronyzobrazami import storage as mod
    from Komponenty.stronyzobrazami.storage import SiteEntry, SiteStore

    monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(mod, "SITES_FILE", tmp_path / "sites.json")

    store = SiteStore(
        sites=[
            SiteEntry(
                id="abc",
                title="Muzeum Test",
                url="https://example.org/art",
                category="Muzeum",
            ),
        ],
    )
    mod.save_sites(store)
    loaded = mod.load_sites()
    assert len(loaded.sites) == 1
    assert loaded.sites[0].title == "Muzeum Test"
