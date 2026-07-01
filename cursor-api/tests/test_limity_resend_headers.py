"""Resend wymaga User-Agent — test nagłówków w collectors."""

from __future__ import annotations

from Komponenty.limity.collectors import USER_AGENT, _http_get_json


def test_http_get_json_includes_user_agent(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeResp:
        def read(self) -> bytes:
            return b"{}"

        @property
        def headers(self) -> dict[str, str]:
            return {"x-resend-monthly-quota": "5"}

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def fake_urlopen(req, **kwargs):  # noqa: ANN001
        captured["User-Agent"] = req.headers.get("User-agent") or req.headers.get("User-Agent", "")
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    _http_get_json("https://example.com", headers={"Authorization": "Bearer x"})
    assert captured["User-Agent"] == USER_AGENT
