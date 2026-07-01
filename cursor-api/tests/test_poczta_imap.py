"""Testy parserów poczty (bez połączenia IMAP)."""

from __future__ import annotations

import email
from email.message import EmailMessage

from Komponenty.poczta.imap_client import (
    _body_preview_from_message,
    _decode_mime,
    _format_date,
    _parse_fetch_meta,
    _strip_html,
)


def test_decode_mime_utf8_subject() -> None:
    raw = "=?utf-8?B?VGVzdCB0ZW1hdA==?="
    assert _decode_mime(raw) == "Test temat"


def test_strip_html_removes_tags() -> None:
    html = "<p>Hello <b>world</b></p><script>x</script>"
    assert _strip_html(html) == "Hello world"


def test_parse_fetch_meta_flags_and_gmail_ids() -> None:
    raw = (
        b'1 (FLAGS (\\Seen \\Flagged) UID 42 '
        b'X-GM-MSGID 123456789 X-GM-THRID 987654321)'
    )
    meta = _parse_fetch_meta(raw)
    assert meta["FLAGS"] == "\\Seen \\Flagged"
    assert meta["X-GM-MSGID"] == "123456789"
    assert meta["X-GM-THRID"] == "987654321"


def test_body_preview_plain_text() -> None:
    msg = EmailMessage()
    msg.set_content("Pierwsza linia\nDruga linia")
    assert "Pierwsza linia" in _body_preview_from_message(msg)


def test_body_preview_fallback_from_html() -> None:
    msg = EmailMessage()
    msg.add_alternative("<html><body><p>Treść HTML</p></body></html>", subtype="html")
    preview = _body_preview_from_message(msg)
    assert "Treść HTML" in preview


def test_uid_bytes() -> None:
    from Komponenty.poczta.imap_client import _uid_bytes

    assert _uid_bytes("12345") == b"12345"


def test_delete_empty_list() -> None:
    from Komponenty.poczta.imap_client import delete_inbox_messages

    assert delete_inbox_messages([]) == 0


def test_format_date_from_header() -> None:
    msg = email.message_from_string(
        "From: a@b.c\nDate: Wed, 3 Jun 2026 14:30:00 +0200\n\nbody"
    )
    formatted = _format_date(msg)
    assert "2026" in formatted
    assert "14:30" in formatted or "12:30" in formatted  # strefa lokalna
