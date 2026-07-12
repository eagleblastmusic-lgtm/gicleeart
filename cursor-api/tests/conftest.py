"""Wspólne, hermetyczne fixture'y testów Stage 2 CI."""

from __future__ import annotations

import tkinter as tk
import urllib.request
from collections.abc import Generator
from typing import Any

import pytest

from tools.stage2_tcl_retry import (
    call_tk_init_with_transient_retry,
    ci_tcl_retry_enabled,
)

_ARTIC_TEST_NODE = (
    "tests/test_stronyzobrazami_search.py::test_artic_fetch_with_referer"
)
_ARTIC_JPEG = b"\xff\xd8fixture-jpeg"


@pytest.fixture(autouse=True)
def _retry_transient_tcl_init_once(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Retry one exact init.tcl read failure only on GitHub Actions."""

    if not ci_tcl_retry_enabled():
        yield
        return

    original_init = tk.Tk.__init__

    def _wrapped_init(self: tk.Tk, *args: object, **kwargs: object) -> None:
        call_tk_init_with_transient_retry(
            original_init,
            self,
            args,
            kwargs,
        )

    monkeypatch.setattr(tk.Tk, "__init__", _wrapped_init)
    yield


@pytest.fixture(autouse=True)
def _hermetic_artic_fetch_contract(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Zastąp sieć wyłącznie w teście kontraktu nagłówków Artic IIIF."""
    node_id = request.node.nodeid.replace("\\", "/")
    if not node_id.endswith(_ARTIC_TEST_NODE):
        yield
        return

    from Komponenty.stronyzobrazami.search import thumbnails
    from Komponenty.stronyzobrazami.search.artic_images import (
        ARTIC_REFERER,
        artic_preview_url,
    )

    expected_url = artic_preview_url(
        "3c27b499-af56-f0d5-93b5-a7f2f1ad5813"
    )
    calls: list[tuple[urllib.request.Request, float]] = []

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def read(self, size: int = -1) -> bytes:
            if size is None or size < 0:
                return _ARTIC_JPEG
            return _ARTIC_JPEG[:size]

    def fake_urlopen(
        http_request: urllib.request.Request,
        *,
        timeout: float,
    ) -> Response:
        calls.append((http_request, timeout))
        return Response()

    thumbnails.clear_cache()
    monkeypatch.setattr(thumbnails, "urlopen", fake_urlopen)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    try:
        yield
    finally:
        thumbnails.clear_cache()

    assert len(calls) == 2
    for http_request, timeout in calls:
        assert http_request.full_url == expected_url
        assert http_request.get_header("Referer") == ARTIC_REFERER
        assert http_request.get_header("Accept") == "image/*"
        assert timeout == 20
