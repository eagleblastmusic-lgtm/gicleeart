"""Tymczasowy hosting obrazu pod publicznym URL (potrzebny dla SerpAPI Google Lens).

Strategia uploadu - WERSJA RACE:
1) Wysylamy obraz JEDNOCZESNIE do 0x0.st i catbox.moe.
2) Bierzemy URL od tego, ktory zwroci jako PIERWSZY (typowo 1-3s).
3) Drugi (jesli wciaz w trakcie) - zostawiamy w spokoju, jego odpowiedz porzucamy.

Dzieki temu nie czekamy 5-15s na powolne 0x0.st, zeby DOPIERO potem proboowac
catbox - oba hosty pracuja rownolegle i wygrywa szybszy. Przed uploadem obraz
jest skalowany do max 1.5 MB (image_prepare.prepare_for_upload).
"""

from __future__ import annotations

import secrets
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from .image_prepare import DEFAULT_MAX_BYTES, PreparedImage, prepare_for_upload


class UploadError(RuntimeError):
    pass


# Krotsze timeouty: typowy upload <2s; jesli serwer nie odpowiada w 30s, trudno
# liczyc na 90s. Drugi host i tak rownolegle juz jedzie.
_DEFAULT_HOST_TIMEOUT = 30.0


@dataclass
class _HostResult:
    name: str
    url: str
    elapsed: float


def _build_multipart(
    filename: str,
    data: bytes,
    mime: str,
    *,
    file_field: str = "file",
    extra_fields: dict[str, str] | None = None,
) -> tuple[bytes, str]:
    boundary = "----nazwijobraz" + secrets.token_hex(12)
    fname = filename.encode("utf-8", errors="replace").decode("latin-1", errors="replace")
    parts: list[bytes] = []
    if extra_fields:
        for k, v in extra_fields.items():
            parts.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
                    f"{v}\r\n"
                ).encode("utf-8")
            )
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; filename="{fname}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def _do_post(
    url: str,
    body: bytes,
    content_type: str,
    *,
    timeout: float,
    user_agent: str,
) -> str:
    """POST z keep-alive (requests.Session) z fallback urllib."""
    try:
        from .http_client import get_session
        sess = get_session()
        try:
            resp = sess.post(
                url,
                data=body,
                headers={
                    "Content-Type": content_type,
                    "User-Agent": user_agent,
                    "Accept": "*/*",
                },
                timeout=timeout,
            )
        except Exception as e:  # noqa: BLE001
            raise urllib.error.URLError(str(e)) from e
        if resp.status_code >= 400:
            raise urllib.error.HTTPError(
                url, resp.status_code, resp.reason or "HTTP error",
                hdrs=resp.headers, fp=None,  # type: ignore[arg-type]
            )
        return (resp.text or "").strip()
    except ImportError:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": content_type,
                "User-Agent": user_agent,
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()


def _upload_0x0(prepared: PreparedImage, *, timeout: float) -> _HostResult:
    body, ct = _build_multipart(prepared.filename, prepared.data, prepared.mime)
    t0 = time.monotonic()
    out = _do_post(
        "https://0x0.st",
        body, ct,
        timeout=timeout,
        user_agent="nazwijobraz/1.0 (+https://0x0.st)",
    )
    if not out.startswith("http"):
        raise UploadError(f"0x0.st: nieoczekiwana odpowiedz: {out[:200]!r}")
    return _HostResult("0x0.st", out, time.monotonic() - t0)


def _upload_catbox(prepared: PreparedImage, *, timeout: float) -> _HostResult:
    body, ct = _build_multipart(
        prepared.filename,
        prepared.data,
        prepared.mime,
        file_field="fileToUpload",
        extra_fields={"reqtype": "fileupload"},
    )
    t0 = time.monotonic()
    out = _do_post(
        "https://catbox.moe/user/api.php",
        body, ct,
        timeout=timeout,
        user_agent="nazwijobraz/1.0",
    )
    if not out.startswith("http"):
        raise UploadError(f"catbox.moe: nieoczekiwana odpowiedz: {out[:200]!r}")
    return _HostResult("catbox.moe", out, time.monotonic() - t0)


def _upload_uguu(prepared: PreparedImage, *, timeout: float) -> _HostResult:
    """uguu.se - tymczasowy hosting (24h), bez API key.

    POST https://uguu.se/upload, multipart files[]=...
    Odpowiedz JSON: {"success":true,"files":[{"url":"https://a.uguu.se/xxx.jpg"}]}
    Wybralismy go bo:
    - pliki sa pod URL-em a.uguu.se (subdomena), Google/Yandex/Bing zazwyczaj
      indeksuja takie hosty lepiej niz catbox.moe (catbox jest na czarnych listach
      czesci crawlerow przez problemy z grey content).
    - 1 endpoint, brak auth, prosty multipart.
    """
    body, ct = _build_multipart(
        prepared.filename,
        prepared.data,
        prepared.mime,
        file_field="files[]",
    )
    t0 = time.monotonic()
    out = _do_post(
        "https://uguu.se/upload",
        body, ct,
        timeout=timeout,
        user_agent="nazwijobraz/1.0",
    )
    # Parser JSON-a; uguu czasem dolepia bialymi znakami.
    import json as _json
    try:
        data = _json.loads(out)
    except _json.JSONDecodeError as e:
        raise UploadError(f"uguu.se: niepoprawny JSON: {e}; head={out[:120]!r}")
    if not isinstance(data, dict) or not data.get("success"):
        raise UploadError(f"uguu.se: success=false: {out[:200]!r}")
    files = data.get("files") or []
    if not isinstance(files, list) or not files:
        raise UploadError(f"uguu.se: brak files w odpowiedzi: {out[:200]!r}")
    url = (files[0] or {}).get("url") if isinstance(files[0], dict) else None
    if not url or not str(url).startswith("http"):
        raise UploadError(f"uguu.se: brak url w files[0]: {out[:200]!r}")
    return _HostResult("uguu.se", str(url), time.monotonic() - t0)


# Globalny pool dla uploadow - max 4 watki * 3 hosty = 12 jednoczesnych uploadow,
# wystarczajace dla zazwyczaj 1-6 plikow w kolejce nazwijobraz.
_UPLOAD_POOL = ThreadPoolExecutor(max_workers=12, thread_name_prefix="upload")

# Lista hostow do uzycia w race upload. Format: (nazwa, funkcja).
# Kolejnosc tu nie ma znaczenia - to RACE, wszyscy startuja naraz.
# Preferencja PER-CONSUMER (Lens / Yandex / Bing) jest w `visual_search.py`.
_UPLOAD_HOSTS: tuple[tuple[str, "callable"], ...] = (  # type: ignore[name-defined]
    ("0x0.st",     _upload_0x0),
    ("catbox.moe", _upload_catbox),
    ("uguu.se",    _upload_uguu),
)


def upload_image(
    file_path: str | Path,
    *,
    timeout: float = _DEFAULT_HOST_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[str, int]:
    """Uplouduje plik pod publiczny URL.

    Strategia RACE: wysyla rownolegle do 0x0.st i catbox.moe, zwraca URL od
    tego, ktory zwroci jako pierwszy. Drugi upload (jesli wciaz trwa) jest
    zostawiony "w tle" - jego odpowiedz po prostu wyrzucamy.

    Returns:
        (url, bytes_wyslane)

    Raises:
        UploadError: gdy OBA hostingi zawioda.
    """
    p = Path(file_path)
    if not p.is_file():
        raise UploadError(f"Plik nie istnieje: {p}")
    try:
        prepared = prepare_for_upload(p, max_bytes=max_bytes)
    except Exception as e:
        raise UploadError(f"Nie udalo sie przygotowac obrazu: {e}") from e

    pending: set[Future[_HostResult]] = {
        _UPLOAD_POOL.submit(fn, prepared, timeout=timeout)
        for _name, fn in _UPLOAD_HOSTS
    }
    errors: list[str] = []

    while pending:
        done, pending = wait(pending, return_when=FIRST_COMPLETED, timeout=timeout + 5)
        if not done:
            for f in pending:
                f.cancel()
            raise UploadError(
                "Wszystkie hostingi nie odpowiedzialy w czasie "
                + (", ".join(errors) if errors else f"{int(timeout)}s")
            )
        for fut in done:
            try:
                res = fut.result()
                # Sukces! Pozostale uploady zostawiamy - nie warto czekac/cancelować
                # bo cancel na uruchomionym Future i tak nie dziala.
                return (res.url, len(prepared.data))
            except (UploadError, urllib.error.HTTPError, urllib.error.URLError, Exception) as e:  # noqa: BLE001
                # jeden host padl - czekamy na pozostale
                errors.append(f"{type(e).__name__}: {e}")

    raise UploadError("Wszystkie hostingi zawiodly: " + " | ".join(errors))


# Maksymalny dodatkowy czas, ktory _czekamy_ na drugi host po tym jak pierwszy
# juz zwrocil sukces. Sluzy temu, zeby Lens dostal URL z PREFEROWANEGO hosta
# (0x0.st - Google Lens dziala dla niego znacznie czesciej niz dla catbox).
_SECONDARY_HOST_GRACE = 4.0


def upload_image_all_urls(
    file_path: str | Path,
    *,
    timeout: float = _DEFAULT_HOST_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    grace_for_secondary: float = _SECONDARY_HOST_GRACE,
) -> tuple[dict[str, str], int, list[str]]:
    """Wgrywa rownolegle do wszystkich hostingow i zwraca WSZYSTKIE URL-e, ktore zd\u0105\u017cy\u0142y.

    Inaczej niz `upload_image` (bierze pierwszy zwycieski), ta funkcja:
    1) Czeka na pierwszy sukces (analogicznie - 1-3s typowo).
    2) Jesli zwyciezca to NIE jest preferowany host (0x0.st),
       jeszcze przez `grace_for_secondary` sekund czeka aby drugi tez sie skonczyl.
    3) Zwraca slownik {nazwa_hosta -> url} z URL-ami WSZYSTKICH ktore sie powiodly.

    Dzieki temu Lens moze dostac URL z 0x0.st (lepszy dla Google), nawet jesli
    catbox zwrocil pierwszy. A pozostali konsumenci moga miec fallback URL.

    Returns:
        (urls_dict, bytes_wyslane, errors_list)
        urls_dict pusty -> oba hostingi zawiodly (errors_list zawiera szczegoly).

    Raises:
        UploadError: gdy plik nie istnieje albo Pillow padlo na przygotowaniu.
    """
    p = Path(file_path)
    if not p.is_file():
        raise UploadError(f"Plik nie istnieje: {p}")
    try:
        prepared = prepare_for_upload(p, max_bytes=max_bytes)
    except Exception as e:
        raise UploadError(f"Nie udalo sie przygotowac obrazu: {e}") from e

    pending = {
        _UPLOAD_POOL.submit(fn, prepared, timeout=timeout)
        for _name, fn in _UPLOAD_HOSTS
    }
    urls: dict[str, str] = {}
    errors: list[str] = []
    first_success_at: float | None = None

    while pending:
        # Po pierwszym sukcesie czekamy juz tylko `grace` sekund na drugi.
        if first_success_at is not None:
            remaining = max(0.0, grace_for_secondary - (time.monotonic() - first_success_at))
            if remaining <= 0:
                break
            wait_timeout = remaining
        else:
            wait_timeout = timeout + 5

        done, pending = wait(pending, return_when=FIRST_COMPLETED, timeout=wait_timeout)
        if not done:
            for f in pending:
                f.cancel()
            break
        for fut in done:
            try:
                res = fut.result()
                urls[res.name] = res.url
                if first_success_at is None:
                    first_success_at = time.monotonic()
            except Exception as e:  # noqa: BLE001
                errors.append(f"{type(e).__name__}: {e}")

    return (urls, len(prepared.data), errors)
