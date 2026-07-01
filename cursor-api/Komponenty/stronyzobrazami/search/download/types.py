"""Typy silnika pobierania obrazow w najlepszej jakosci."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

DownloadStrategy = Literal["iiif", "direct", "page_scrape", "assetbank_post", "none"]


@dataclass
class DownloadSpec:
    strategy: DownloadStrategy
    source_id: str = ""
    title: str = ""
    artist: str = ""
    service_id: str = ""
    direct_url: str = ""
    page_url: str = ""
    suggested_filename: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    width: int = 0
    height: int = 0

    @property
    def ok(self) -> bool:
        if self.strategy == "iiif":
            return bool(self.service_id)
        if self.strategy == "direct":
            return bool(self.direct_url)
        if self.strategy == "page_scrape":
            return bool(self.page_url)
        if self.strategy == "assetbank_post":
            return bool(self.page_url)
        return False


@dataclass
class DownloadProgress:
    phase: str = ""
    done: int = 0
    total: int = 0
    message: str = ""

    @property
    def fraction(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, self.done / self.total)


@dataclass
class DownloadResult:
    ok: bool
    path: str = ""
    width: int = 0
    height: int = 0
    strategy: DownloadStrategy = "none"
    error: str = ""


ProgressCallback = Callable[[DownloadProgress], None]
CancelCheck = Callable[[], bool] | None
