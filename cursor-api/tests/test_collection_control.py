"""Testy kontroli kolekcji (heurystyki, bez API)."""

from __future__ import annotations

from Komponenty.dodajobraz.collection_control import (
    collection_title_matches_expected,
    evaluate_collection_row_status,
    is_probable_artist_collection,
    resolve_artist_collection_in_catalog,
)


def test_is_probable_artist_collection() -> None:
    assert is_probable_artist_collection("Constable, John") is True
    assert is_probable_artist_collection("obraz do salonu") is False
    assert is_probable_artist_collection("") is False


def test_collection_title_matches_expected_canaletto() -> None:
    assert collection_title_matches_expected("Canal, Antonio (Canaletto)", "Canal, Antonio")
    assert not collection_title_matches_expected("Monet, Claude", "Canal, Antonio")


def test_resolve_artist_collection_fuzzy() -> None:
    catalog = {
        1: {"id": 1, "title": "Canal, Antonio (Canaletto)", "kind": "smart"},
        2: {"id": 2, "title": "obraz do salonu", "kind": "smart"},
    }
    meta = resolve_artist_collection_in_catalog(catalog, "Canal, Antonio")
    assert meta is not None
    assert meta["title"] == "Canal, Antonio (Canaletto)"


def test_evaluate_status_ok_when_in_canaletto_collection() -> None:
    catalog = {1: {"id": 1, "title": "Canal, Antonio (Canaletto)", "kind": "smart"}}
    ev = evaluate_collection_row_status(
        artist="Antonio Canal",
        titles={"Canal, Antonio (Canaletto)"},
        catalog=catalog,
    )
    assert ev["status"] == "OK"
    assert ev["in_expected"] is True


def test_collection_title_matches_particle_and_hyphen() -> None:
    assert collection_title_matches_expected("Van Gogh, Vincent", "Gogh, Vincent Van")
    assert collection_title_matches_expected("Daubigny, Charles-François", "Daubigny, Charles François")
    assert collection_title_matches_expected("Da Vinci, Leonardo", "Vinci, Leonardo Da")
    assert collection_title_matches_expected("Van Ruisdael, Jacob", "Ruisdael, Jacob Van")


def test_evaluate_ok_when_shopify_uses_van_gogh_order() -> None:
    catalog = {9: {"id": 9, "title": "Van Gogh, Vincent", "kind": "smart"}}
    ev = evaluate_collection_row_status(
        artist="Vincent Van Gogh",
        titles={"Van Gogh, Vincent", "obraz do salonu"},
        catalog=catalog,
    )
    assert ev["status"] == "OK"
    assert ev["in_expected"] is True
