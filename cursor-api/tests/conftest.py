"""Wspólne, hermetyczne fixture'y testów Stage 2 CI."""

from __future__ import annotations

import os
import time
import tkinter as tk
import urllib.request
from collections.abc import Callable, Generator, Mapping
from pathlib import Path
from typing import Any, TypeVar

import pytest

_ARTIC_TEST_NODE = (
    "tests/test_stronyzobrazami_search.py::test_artic_fetch_with_referer"
)
_ARTIC_JPEG = b"\xff\xd8fixture-jpeg"
_TCL_INIT_SIGNATURE = "Can't find a usable init.tcl"
_T = TypeVar("_T")


def _ci_tcl_retry_enabled(environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return (
        str(env.get("GITHUB_ACTIONS", "")).strip().casefold() == "true"
        and bool(str(env.get("TCL_LIBRARY", "")).strip())
    )


def _is_transient_tcl_init_error(exc: BaseException) -> bool:
    message = str(exc)
    return _TCL_INIT_SIGNATURE in message and "init.tcl" in message


def _wait_for_tcl_init_readable() -> None:
    library = os.environ.get("TCL_LIBRARY", "").strip()
    if not library:
        return

    init_file = Path(library) / "init.tcl"
    for delay in (0.0, 0.05, 0.15):
        if delay:
            time.sleep(delay)
        try:
            init_file.read_bytes()
            return
        except OSError:
            continue

    # Nie maskuj problemu. Druga próba Tk zgłosi pełny TclError, ale krótki
    # read probe daje systemowi plików czas na zwolnienie przejściowej blokady.


def _call_tk_init_with_transient_retry(
    original: Callable[..., _T],
    instance: object,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> _T:
    try:
        return original(instance, *args, **kwargs)
    except tk.TclError as exc:
        if not _is_transient_tcl_init_error(exc):
            raise
        _wait_for_tcl_init_readable()
        # Dokładnie jedna dodatkowa próba. Każdy kolejny błąd pozostaje
        # normalnym, blokującym failure testu.
        return original(instance, *args, **kwargs)


@pytest.fixture(autouse=True)
def _retry_transient_tcl_init_once(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Retry one exact init.tcl read failure only on GitHub Actions."""

    if not _ci_tcl_retry_enabled():
        yield
        return

    original_init = tk.Tk.__init__

    def _wrapped_init(self: tk.Tk, *args: object, **kwargs: object) -> None:
        _call_tk_init_with_transient_retry(
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
