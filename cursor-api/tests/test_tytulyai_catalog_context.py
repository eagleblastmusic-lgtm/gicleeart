"""Testy unikania kolizji tytulow w katalogu."""
from Komponenty.tytulyai.catalog_context import (
    collision_warning,
    find_pl_title_collision,
    other_pl_titles_for_artist,
    pl_title_primary,
)


def test_pl_title_primary() -> None:
    assert pl_title_primary("Latający Holender (lub koga)") == "Latający Holender"


def test_collision_same_artist() -> None:
    rows = [
        {"product_id": 1, "artist": "Diemer", "painting_title": "Latający Holender"},
        {"product_id": 2, "artist": "Diemer", "painting_title": "Latający Holender"},
    ]
    warn = collision_warning(
        "Latający Holender",
        artist="Diemer",
        product_id=2,
        catalog_rows=rows,
    )
    assert "KOLIZJA" in warn


def test_no_collision_different_primary() -> None:
    rows = [
        {"product_id": 1, "artist": "Diemer", "painting_title": "Latający Holender"},
        {"product_id": 2, "artist": "Diemer", "painting_title": "Trójmasztowiec na morzu"},
    ]
    assert find_pl_title_collision(
        "Trójmasztowiec w Cieśninie",
        artist="Diemer",
        product_id=99,
        catalog_rows=rows,
    ) is None


def test_other_pl_titles_for_artist() -> None:
    rows = [
        {"product_id": 1, "artist": "A", "painting_title": "X"},
        {"product_id": 2, "artist": "A", "painting_title": "Y"},
        {"product_id": 3, "artist": "B", "painting_title": "Z"},
    ]
    assert other_pl_titles_for_artist(rows, artist="A", exclude_product_id=2) == ["X"]
