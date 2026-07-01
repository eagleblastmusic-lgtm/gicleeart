"""Pobieranie wiadomości z Gmail przez IMAP (hasło aplikacji)."""

from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from typing import Any

from .env_config import gmail_imap_password, gmail_imap_user

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
DEFAULT_LIMIT = 40
HEADER_FETCH = "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] FLAGS X-GM-MSGID X-GM-THRID)"
BODY_FETCH = "(BODY.PEEK[] FLAGS)"
BATCH_SIZE = 30


@dataclass(frozen=True)
class MailMessage:
    uid: str
    from_addr: str
    subject: str
    date_display: str
    snippet: str
    body_preview: str
    is_unseen: bool
    gmail_msgid: str | None
    gmail_thrid: str | None


class ImapConfigError(RuntimeError):
    """Brak hasła lub błędna konfiguracja."""


class ImapFetchError(RuntimeError):
    """Błąd połączenia lub odczytu skrzynki."""


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (email.errors.HeaderParseError, UnicodeError, ValueError):
        return value.strip()


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _body_preview_from_message(msg: email.message.Message, limit: int = 1200) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if part.get_content_type() == "text/plain":
                plain_parts.append(text)
            elif part.get_content_type() == "text/html":
                html_parts.append(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)

    body = "\n".join(plain_parts).strip()
    if not body and html_parts:
        body = _strip_html("\n".join(html_parts))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) > limit:
        return body[: limit - 1] + "…"
    return body


def _parse_fetch_meta(raw: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    text = raw.decode("utf-8", errors="replace")
    for key in ("X-GM-MSGID", "X-GM-THRID"):
        m = re.search(rf"{key}\s+(\d+)", text)
        if m:
            out[key] = m.group(1)
    flags_m = re.search(r"FLAGS \(([^)]*)\)", text)
    if flags_m:
        out["FLAGS"] = flags_m.group(1)
    return out


def _format_date(msg: email.message.Message) -> str:
    raw = msg.get("Date")
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo:
            dt = dt.astimezone()
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OverflowError):
        return _decode_mime(raw)


GMAIL_TRASH_CANDIDATES = ("[Gmail]/Trash", "[Gmail]/Kosz", "[Gmail]/Bin")


def _require_password() -> str:
    password = gmail_imap_password()
    if not password:
        raise ImapConfigError(
            "Brak GMAIL_IMAP_APP_PASSWORD w cursor-api/.env — "
            "wygeneruj hasło aplikacji Google (konto z 2FA)."
        )
    return password


def _connect(readonly: bool = True) -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(gmail_imap_user(), _require_password())
    status, _ = imap.select("INBOX", readonly=readonly)
    if status != "OK":
        imap.logout()
        raise ImapFetchError("Nie można otworzyć skrzynki INBOX.")
    return imap


def _gmail_trash_mailbox(imap: imaplib.IMAP4_SSL) -> str:
    for name in GMAIL_TRASH_CANDIDATES:
        status, _ = imap.select(name, readonly=True)
        if status == "OK":
            imap.select("INBOX", readonly=False)
            return name
    return GMAIL_TRASH_CANDIDATES[0]


def _uid_bytes(uid: str) -> bytes:
    return uid.encode("ascii") if isinstance(uid, str) else bytes(uid)


def delete_inbox_messages(uids: list[str]) -> int:
    """Przenosi wiadomości do Kosza Gmail i usuwa z INBOX. Zwraca liczbę usuniętych."""
    if not uids:
        return 0

    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = _connect(readonly=False)
        trash = _gmail_trash_mailbox(imap)
        deleted = 0
        for uid in uids:
            uid_b = _uid_bytes(uid)
            status_copy, _ = imap.uid("COPY", uid_b, trash)
            if status_copy != "OK":
                continue
            status_store, _ = imap.uid("STORE", uid_b, "+FLAGS", "(\\Deleted)")
            if status_store == "OK":
                deleted += 1
        if deleted:
            imap.expunge()
        return deleted
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(f"IMAP: {exc}") from exc
    finally:
        if imap is not None:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass


def _parse_imap_status(data: list[bytes | None] | None) -> dict[str, int]:
    if not data or not data[0]:
        return {"unseen": 0, "total": 0}
    text = data[0].decode("utf-8", errors="replace") if isinstance(data[0], bytes) else str(data[0])
    m_total = re.search(r"MESSAGES\s+(\d+)", text)
    m_unseen = re.search(r"UNSEEN\s+(\d+)", text)
    return {
        "total": int(m_total.group(1)) if m_total else 0,
        "unseen": int(m_unseen.group(1)) if m_unseen else 0,
    }


def _uid_from_fetch_meta(meta_raw: bytes) -> str:
    m = re.search(rb"UID\s+(\d+)", meta_raw)
    return m.group(1).decode("ascii") if m else ""


def _parse_header_fetch_items(fetched: list[Any]) -> list[MailMessage]:
    out: list[MailMessage] = []
    if not fetched:
        return out
    for part in fetched:
        if part is None or part == b")":
            continue
        if not isinstance(part, tuple) or len(part) < 2:
            continue
        meta_raw, body_raw = part[0], part[1]
        if not isinstance(meta_raw, bytes) or not isinstance(body_raw, bytes):
            continue
        uid_s = _uid_from_fetch_meta(meta_raw)
        if not uid_s:
            continue
        meta = _parse_fetch_meta(meta_raw)
        flags = meta.get("FLAGS", "")
        msg = email.message_from_bytes(body_raw)
        from_addr = _decode_mime(msg.get("From"))
        subject = _decode_mime(msg.get("Subject")) or "(bez tematu)"
        out.append(
            MailMessage(
                uid=uid_s,
                from_addr=from_addr,
                subject=subject,
                date_display=_format_date(msg),
                snippet=subject[:140] + ("…" if len(subject) > 140 else ""),
                body_preview="",
                is_unseen="\\Seen" not in flags,
                gmail_msgid=meta.get("X-GM-MSGID"),
                gmail_thrid=meta.get("X-GM-THRID"),
            )
        )
    return out


def _chunk_uids(uids: list[bytes], size: int) -> list[list[bytes]]:
    return [uids[i : i + size] for i in range(0, len(uids), size)]


def fetch_inbox_overview(
    *, limit: int = DEFAULT_LIMIT, unseen_only: bool = False
) -> tuple[dict[str, int], list[MailMessage]]:
    """Jedno połączenie IMAP: STATUS + nagłówki wiadomości (treść ładowana osobno)."""
    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = _connect(readonly=True)
        _, status_data = imap.status("INBOX", "(MESSAGES UNSEEN)")
        stats = _parse_imap_status(status_data)

        criteria = "UNSEEN" if unseen_only else "ALL"
        status, data = imap.uid("search", None, criteria)
        if status != "OK" or not data or not data[0]:
            return stats, []

        uids = data[0].split()
        uids = uids[-limit:]
        uids.reverse()
        if not uids:
            return stats, []

        messages: list[MailMessage] = []
        for chunk in _chunk_uids(uids, BATCH_SIZE):
            uid_arg = b",".join(chunk)
            status, fetched = imap.uid("fetch", uid_arg, HEADER_FETCH)
            if status != "OK" or not fetched:
                continue
            messages.extend(_parse_header_fetch_items(fetched))
        by_uid = {m.uid: m for m in messages}
        ordered: list[MailMessage] = []
        for uid in uids:
            uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
            msg = by_uid.get(uid_s)
            if msg is not None:
                ordered.append(msg)
        return stats, ordered
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(f"IMAP: {exc}") from exc
    finally:
        if imap is not None:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass


def _extract_html_from_message(msg: email.message.Message) -> str:
    html_parts: list[str] = []
    plain_parts: list[str] = []

    def _collect(part: email.message.Message) -> None:
        if part.is_multipart():
            for sub in part.get_payload():
                if isinstance(sub, email.message.Message):
                    _collect(sub)
            return
        disp = (part.get("Content-Disposition") or "").lower()
        if "attachment" in disp:
            return
        payload = part.get_payload(decode=True)
        if not payload:
            return
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")
        ctype = (part.get_content_type() or "").lower()
        if ctype == "text/html":
            html_parts.append(text)
        elif ctype == "text/plain":
            plain_parts.append(text)

    _collect(msg)
    if html_parts:
        return "\n".join(html_parts)
    if plain_parts:
        esc = "\n".join(plain_parts).replace("&", "&amp;").replace("<", "&lt;")
        return f"<pre>{esc}</pre>"
    return ""


def fetch_message_html(uid: str) -> str:
    """Treść HTML wiadomości (parsowanie linków zamówień)."""
    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = _connect(readonly=True)
        status, fetched = imap.uid("fetch", _uid_bytes(uid), BODY_FETCH)
        if status != "OK" or not fetched or fetched[0] is None:
            return ""
        part = fetched[0]
        if not isinstance(part, tuple) or len(part) < 2:
            return ""
        body_raw = part[1]
        if not isinstance(body_raw, bytes):
            return ""
        msg = email.message_from_bytes(body_raw)
        return _extract_html_from_message(msg)
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(f"IMAP: {exc}") from exc
    finally:
        if imap is not None:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass


def fetch_message_body(uid: str, *, limit: int = 1200) -> str:
    """Pełna treść wiadomości — osobne, krótkie połączenie po kliknięciu."""
    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = _connect(readonly=True)
        status, fetched = imap.uid("fetch", _uid_bytes(uid), BODY_FETCH)
        if status != "OK" or not fetched or fetched[0] is None:
            return "(nie udało się pobrać treści)"
        part = fetched[0]
        if not isinstance(part, tuple) or len(part) < 2:
            return "(nie udało się pobrać treści)"
        body_raw = part[1]
        if not isinstance(body_raw, bytes):
            return "(nie udało się pobrać treści)"
        msg = email.message_from_bytes(body_raw)
        preview = _body_preview_from_message(msg, limit=limit)
        return preview or "(brak treści tekstowej)"
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(f"IMAP: {exc}") from exc
    finally:
        if imap is not None:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass


def fetch_inbox_messages(*, limit: int = DEFAULT_LIMIT, unseen_only: bool = False) -> list[MailMessage]:
    """Pobiera ostatnie wiadomości z INBOX (nagłówki; treść przez fetch_message_body)."""
    _, messages = fetch_inbox_overview(limit=limit, unseen_only=unseen_only)
    return messages


def inbox_stats() -> dict[str, Any]:
    """Liczba wszystkich i nieprzeczytanych (STATUS — bez listowania UID)."""
    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = _connect(readonly=True)
        _, status_data = imap.status("INBOX", "(MESSAGES UNSEEN)")
        return _parse_imap_status(status_data)
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(f"IMAP: {exc}") from exc
    finally:
        if imap is not None:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass
