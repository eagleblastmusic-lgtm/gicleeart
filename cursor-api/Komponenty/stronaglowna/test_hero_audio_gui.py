from __future__ import annotations

from .hero_audio_gui import _AUDIO_UPLOAD_TOAST, _notify_audio_uploaded


def test_audio_upload_toast_receives_parent_widget_first() -> None:
    parent = object()
    calls: list[tuple[object, str]] = []

    def fake_show_toast(actual_parent: object, text: str) -> None:
        calls.append((actual_parent, text))

    _notify_audio_uploaded(fake_show_toast, parent)  # type: ignore[arg-type]

    assert calls == [(parent, _AUDIO_UPLOAD_TOAST)]
