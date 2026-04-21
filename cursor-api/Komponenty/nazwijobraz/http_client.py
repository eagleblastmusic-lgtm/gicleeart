"""HTTP client z keep-alive (`requests.Session`) wspoldzielonym przez wszystkie modu\u0142y.

Powod: kazde nowe polaczenie HTTPS to dodatkowy roundtrip TLS handshake (~100-300 ms
na zapytanie). Wikidata/Commons/Met/ArtIC/Wikipedia/SerpAPI obslugujemy w petli, wiec
recykling polaczen daje +20-30% szybkosci wyszukiwania.

Dodatkowo: HTTP retry (3 proby, exponential backoff) na 500/502/503/504/429.
Connection pool ustawiony na 20 - matchujemy max liczbe rownoleglych watkow w GUI
(_SEARCH_WORKERS=6 * _PER_FILE_SOURCE_WORKERS=5 = 30, ale zwykle nie wszystko jednoczesnie).
"""

from __future__ import annotations

import json
import threading
from typing import Any

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Modul 'requests' jest wymagany. Zainstaluj: pip install requests"
    ) from e

try:
    # urllib3>=1.26 ma Retry w urllib3.util.retry; >=2.0 tez tam jest.
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover
    Retry = None  # type: ignore[assignment]


_DEFAULT_USER_AGENT = "nazwijobraz/1.0 (+https://github.com/cursor-api)"
_POOL_MAXSIZE = 20

_session_lock = threading.Lock()
_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Zwraca wspolny singleton `requests.Session` z keep-alive."""
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        s = requests.Session()
        s.headers.update({"User-Agent": _DEFAULT_USER_AGENT})
        if Retry is not None:
            retry = Retry(
                total=3,
                connect=3,
                read=2,
                backoff_factor=0.5,            # 0s, 0.5s, 1s, 2s
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET", "HEAD", "POST"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(
                pool_connections=_POOL_MAXSIZE,
                pool_maxsize=_POOL_MAXSIZE,
                max_retries=retry,
            )
            s.mount("https://", adapter)
            s.mount("http://", adapter)
        _session = s
        return _session


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 12.0,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET + JSON parse. Zwraca dict/list lub None gdy fail."""
    sess = get_session()
    try:
        resp = sess.get(url, params=params, timeout=timeout, headers=headers)
        if resp.status_code >= 400:
            return None
        try:
            return resp.json()
        except json.JSONDecodeError:
            return None
    except requests.RequestException:
        return None


def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 12.0,
    headers: dict[str, str] | None = None,
) -> str:
    """GET + tekst. Zwraca '' gdy fail."""
    sess = get_session()
    try:
        resp = sess.get(url, params=params, timeout=timeout, headers=headers)
        if resp.status_code >= 400:
            return ""
        return resp.text or ""
    except requests.RequestException:
        return ""


def post(
    url: str,
    *,
    data: Any = None,
    files: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> "requests.Response | None":
    """POST z keep-alive. Zwraca Response lub None na blad sieci."""
    sess = get_session()
    try:
        return sess.post(
            url, data=data, files=files, headers=headers, timeout=timeout,
        )
    except requests.RequestException:
        return None
