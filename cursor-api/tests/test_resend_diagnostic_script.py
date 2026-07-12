"""Testy ręcznego skryptu diagnostycznego Resend."""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "mockup-order-worker"
    / "scripts"
    / "test_resend.py"
)


def _load_script() -> ModuleType:
    module_name = "giclee_resend_diagnostic_script"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_import_has_no_network_or_process_exit(monkeypatch) -> None:  # noqa: ANN001
    def fail_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network access during import")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    module = _load_script()

    assert callable(module.main)
    assert callable(module.send_test_email)


def test_resolve_api_key_reads_isolated_env_file(
    monkeypatch,
    tmp_path: Path,
) -> None:  # noqa: ANN001
    module = _load_script()
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# comment\nRESEND_API_KEY='test-key'\nIGNORED_LINE\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    assert module.resolve_api_key(env_path) == "test-key"


def test_build_request_contains_expected_contract() -> None:
    module = _load_script()

    request = module.build_request(
        "secret-key",
        recipient="recipient@example.com",
    )

    assert request.full_url == module.RESEND_ENDPOINT
    assert request.method == "POST"
    assert request.get_header("Authorization") == "Bearer secret-key"
    assert request.get_header("Content-type") == "application/json"

    payload = json.loads(request.data.decode("utf-8"))
    assert payload["to"] == ["recipient@example.com"]
    assert payload["subject"] == "Test Giclee mockup worker"


def test_send_test_email_uses_injected_opener() -> None:
    module = _load_script()
    captured: dict[str, object] = {}

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return b'{"id":"email-123"}'

    def fake_opener(request, *, timeout):  # noqa: ANN001
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    status, body = module.send_test_email(
        "secret-key",
        opener=fake_opener,
    )

    assert status == 202
    assert body == '{"id":"email-123"}'
    assert captured["timeout"] == 30
    assert captured["request"].full_url == module.RESEND_ENDPOINT


def test_main_without_key_returns_failure_without_network(
    monkeypatch,
    capsys,
) -> None:  # noqa: ANN001
    module = _load_script()
    monkeypatch.setattr(module, "resolve_api_key", lambda: "")

    def fail_send(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("send should not run without an API key")

    monkeypatch.setattr(module, "send_test_email", fail_send)

    assert module.main() == 1
    assert "Brak RESEND_API_KEY" in capsys.readouterr().out


def test_main_success_returns_zero(monkeypatch, capsys) -> None:  # noqa: ANN001
    module = _load_script()
    monkeypatch.setattr(module, "resolve_api_key", lambda: "secret-key")
    monkeypatch.setattr(
        module,
        "send_test_email",
        lambda api_key: (202, '{"id":"email-123"}'),
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "Resend OK" in output
    assert "202" in output
