"""Silnik pobierania obrazow w najlepszej jakosci."""

from .engine import download_hit, download_link, download_spec
from .resolvers import resolve_hit, resolve_url
from .types import DownloadProgress, DownloadResult, DownloadSpec

__all__ = [
    "DownloadProgress",
    "DownloadResult",
    "DownloadSpec",
    "download_hit",
    "download_link",
    "download_spec",
    "resolve_hit",
    "resolve_url",
]
