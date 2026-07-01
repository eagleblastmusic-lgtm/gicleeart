"""Silnik wyszukiwania w kolekcjach muzealnych."""

from .engine import search_collections
from .image_search import ImageSearchResult, search_by_image
from .registry import SOURCES, source_for_url, sources_for_sites
from .types import AggregatedSearch, ArtworkHit, SourceSearchResult

__all__ = [
    "AggregatedSearch",
    "ArtworkHit",
    "ImageSearchResult",
    "SOURCES",
    "SourceSearchResult",
    "search_by_image",
    "search_collections",
    "source_for_url",
    "sources_for_sites",
]
