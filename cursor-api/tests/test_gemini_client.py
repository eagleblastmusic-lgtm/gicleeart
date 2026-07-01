"""Testy klienta Gemini — wykrywanie bledow i retry."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_is_transient_availability_error_503() -> None:
    from Komponenty._shared.gemini_client import (
        GeminiError,
        format_gemini_error,
        is_transient_availability_error,
    )

    exc = GeminiError(
        'HTTP 503: {"error": {"status": "UNAVAILABLE", "message": "high demand"}}',
        status_code=503,
    )
    assert is_transient_availability_error(exc)
    msg = format_gemini_error(exc)
    assert "503" in msg


def test_parse_retry_delay_from_json() -> None:
    from Komponenty._shared.gemini_client import _retry_sleep_seconds

    err = (
        'HTTP 429: {"error":{"details":[{"retryDelay":"47s"}]}}'
    )
    wait = _retry_sleep_seconds(err, 0, rate_limit=True)
    assert wait == pytest.approx(50.0)


def test_503_minimum_wait() -> None:
    from Komponenty._shared.gemini_client import (
        MIN_503_SLEEP_S,
        _retry_sleep_seconds,
    )

    wait = _retry_sleep_seconds(
        'HTTP 503: {"status": "UNAVAILABLE"}',
        0,
        rate_limit=False,
        unavailable=True,
    )
    assert wait >= MIN_503_SLEEP_S


def test_rate_limit_429_minimum_wait() -> None:
    from Komponenty._shared.gemini_client import (
        MIN_RATE_LIMIT_SLEEP_S,
        _retry_sleep_seconds,
    )

    wait = _retry_sleep_seconds("HTTP 429: quota", 0, rate_limit=True)
    assert wait >= MIN_RATE_LIMIT_SLEEP_S


def test_daily_quota_not_retried_forever(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    def fake_post(**kwargs):
        raise gc.GeminiError(
            "HTTP 429: GenerateRequestsPerDay per day limit",
            status_code=429,
        )

    monkeypatch.setattr(gc, "_post_generate", fake_post)

    with pytest.raises(gc.GeminiError) as exc_info:
        gc._generate_with_retries(
            parts=[{"text": "x"}],
            api_key="test-key",
            model=gc.DEFAULT_MODEL,
            timeout=30.0,
        )
    assert "DZIENNY limit" in str(exc_info.value)


def test_billing_credits_not_retried_forever(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    def fake_post(**kwargs):
        raise gc.GeminiError(
            "HTTP 429: Your prepayment credits are depleted.",
            status_code=429,
        )

    monkeypatch.setattr(gc, "_post_generate", fake_post)

    with pytest.raises(gc.GeminiError) as exc_info:
        gc._generate_with_retries(
            parts=[{"text": "x"}],
            api_key="test-key",
            model=gc.DEFAULT_MODEL,
            timeout=30.0,
        )
    assert "kredyty" in str(exc_info.value).lower()


def test_timeout_error_is_retried(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    calls = {"n": 0}

    def fake_post(**kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise gc.GeminiError("Timeout: The read operation timed out")
        return "ok"

    monkeypatch.setattr(gc, "_post_generate", fake_post)
    monkeypatch.setattr(gc, "_sleep_with_status", lambda *_a, **_k: None)

    text, model = gc._generate_with_retries(
        parts=[{"text": "x"}],
        api_key="test-key",
        model=gc.DEFAULT_MODEL,
        timeout=30.0,
    )
    assert text == "ok"
    assert calls["n"] == 2


def test_generate_retries_on_429_until_success(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    calls = {"n": 0}

    def fake_post(**kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise gc.GeminiError('HTTP 429: {"retryDelay":"5s"}', status_code=429)
        return "ok"

    monkeypatch.setattr(gc, "_post_generate", fake_post)
    monkeypatch.setattr(gc, "_sleep_with_status", lambda *_a, **_k: None)

    text, model = gc._generate_with_retries(
        parts=[{"text": "x"}],
        api_key="test-key",
        model=gc.DEFAULT_MODEL,
        timeout=30.0,
    )
    assert text == "ok"
    assert calls["n"] == 3
    assert model == gc.DEFAULT_MODEL


def test_generate_retries_on_503_until_success(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    msg = (
        'HTTP 503: {"error": {"code": 503, "message": "high demand", '
        '"status": "UNAVAILABLE"}}'
    )
    calls = {"n": 0}

    def fake_post(**kwargs):
        calls["n"] += 1
        if calls["n"] < 4:
            raise gc.GeminiError(msg, status_code=503)
        return "ok"

    monkeypatch.setattr(gc, "_post_generate", fake_post)
    monkeypatch.setattr(gc, "_sleep_with_status", lambda *_a, **_k: None)

    text, model = gc._generate_with_retries(
        parts=[{"text": "x"}],
        api_key="test-key",
        model=gc.DEFAULT_MODEL,
        timeout=30.0,
    )
    assert text == "ok"
    assert calls["n"] == 4
    assert model == gc.DEFAULT_MODEL


def test_on_status_exception_does_not_stop_503_retry(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    msg = 'HTTP 503: {"error": {"code": 503, "status": "UNAVAILABLE"}}'
    calls = {"n": 0}

    def fake_post(**kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise gc.GeminiError(msg, status_code=503)
        return "ok"

    def bad_status(_msg: str) -> None:
        raise RuntimeError("UI padlo")

    monkeypatch.setattr(gc, "_post_generate", fake_post)
    monkeypatch.setattr(gc, "_sleep_with_status", lambda *_a, **_k: None)

    text, _model = gc._generate_with_retries(
        parts=[{"text": "x"}],
        api_key="test-key",
        model=gc.DEFAULT_MODEL,
        timeout=30.0,
        on_status=bad_status,
    )
    assert text == "ok"
    assert calls["n"] == 2


def test_should_abort_during_sleep(monkeypatch) -> None:
    from Komponenty._shared import gemini_client as gc

    def fake_post(**kwargs):
        raise gc.GeminiError("HTTP 429: quota", status_code=429)

    monkeypatch.setattr(gc, "_post_generate", fake_post)

    with pytest.raises(gc.GeminiAborted):
        gc._generate_with_retries(
            parts=[{"text": "x"}],
            api_key="test-key",
            model=gc.DEFAULT_MODEL,
            timeout=30.0,
            should_abort=lambda: True,
        )
