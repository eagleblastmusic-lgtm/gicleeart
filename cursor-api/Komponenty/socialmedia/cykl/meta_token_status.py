"""Status wygasniecia tokenow Meta (debug_token + zapis w meta_credentials.json)."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import platforms_cykl as _cp
from .meta_publisher import GRAPH_BASE
from .storage import _CREDS_FILE, load_meta_credentials

KNOWN_CRED_KEYS = frozenset({"page_id", "access_token", "ig_user_id"})
DEFAULT_TOKEN_LIFETIME_DAYS = 60


@dataclass(frozen=True)
class ChannelTokenStatus:
    channel_code: str
    label: str
    configured: bool
    is_valid: bool | None
    expires_at: int | None  # unix; None = nieznane; 0 = bez daty (page token)
    days_left: int | None
    detail: str = ""


@dataclass
class MetaTokenReport:
    channels: list[ChannelTokenStatus] = field(default_factory=list)
    days_left_min: int | None = None
    any_expired: bool = False
    any_missing: bool = False
    note: str = ""


def _env_file_path() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        env = parent / ".env"
        if env.is_file():
            return env
    return None


def _load_dotenv() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        env = parent / ".env"
        if env.is_file():
            for raw in env.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            return


def meta_app_credentials() -> tuple[str, str]:
    _load_dotenv()
    app_id = (os.environ.get("META_APP_ID") or os.environ.get("FACEBOOK_APP_ID") or "").strip()
    app_secret = (
        os.environ.get("META_APP_SECRET") or os.environ.get("FACEBOOK_APP_SECRET") or ""
    ).strip()
    return app_id, app_secret


def discover_app_id_from_credentials() -> str:
    """App ID z debug_token na zapisanym tokenie (bez App Secret)."""
    try:
        creds = load_meta_credentials()
        for code in ("fb_pl", "fb_en", "ig_pl", "ig_en"):
            entry = creds.get(code) or {}
            token = (entry.get("access_token") or "").strip()
            if not token:
                continue
            data = debug_access_token(token)
            app_id = str(data.get("app_id") or "").strip()
            if app_id:
                return app_id
    except Exception:
        pass
    return ""


def save_meta_app_credentials(app_id: str, app_secret: str) -> None:
    """Zapisuje META_APP_ID i META_APP_SECRET do cursor-api/.env."""
    app_id = (app_id or "").strip()
    app_secret = (app_secret or "").strip()
    if not app_id or not app_secret:
        raise ValueError("App ID i App Secret są wymagane.")
    path = _env_file_path()
    if path is None:
        raise RuntimeError("Nie znaleziono pliku cursor-api/.env")

    values = {"META_APP_ID": app_id, "META_APP_SECRET": app_secret}
    lines = path.read_text(encoding="utf-8").splitlines()
    found = dict.fromkeys(values, False)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key, _, _ = stripped.partition("=")
        key = key.strip()
        if key in values:
            out.append(f"{key}={values[key]}")
            found[key] = True
        else:
            out.append(line)

    if not all(found.values()):
        if out and out[-1].strip():
            out.append("")
        out.append("# Meta Graph API — kreator tokenów (Limity)")
        for key, val in values.items():
            if not found[key]:
                out.append(f"{key}={val}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ["META_APP_ID"] = app_id
    os.environ["META_APP_SECRET"] = app_secret


def debug_access_token(token: str) -> dict:
    """Wywoluje Graph API debug_token. Zwraca pole `data` lub pusty dict."""
    token = (token or "").strip()
    if not token:
        return {}
    app_id, app_secret = meta_app_credentials()
    if app_id and app_secret:
        access_token = f"{app_id}|{app_secret}"
    else:
        access_token = token
    qs = urllib.parse.urlencode({"input_token": token, "access_token": access_token})
    url = f"{GRAPH_BASE}/debug_token?{qs}"
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "GicleeApp/1.0"})
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return {}
    except (json.JSONDecodeError, OSError, TimeoutError):
        return {}
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, dict) else {}


def _expires_unix(data: dict) -> int | None:
    exp = data.get("expires_at")
    if exp is None:
        da = data.get("data_access_expires_at")
        exp = da
    try:
        val = int(exp)
    except (TypeError, ValueError):
        return None
    return val


def _days_left_from_expires(expires_at: int | None) -> int | None:
    if expires_at is None:
        return None
    if expires_at == 0:
        return None  # bez daty wygaśnięcia
    now = datetime.now(timezone.utc).timestamp()
    return max(0, int((expires_at - now) // 86400))


def _read_raw_creds() -> dict:
    if not _CREDS_FILE.is_file():
        return {}
    try:
        raw = json.loads(_CREDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _estimate_days_from_checked(checked_iso: str) -> int | None:
    try:
        checked = datetime.fromisoformat(checked_iso)
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    age_days = (datetime.now(timezone.utc) - checked.astimezone(timezone.utc)).days
    return max(0, DEFAULT_TOKEN_LIFETIME_DAYS - age_days)


def _latest_renewal_iso(raw: dict, entry: dict | None = None) -> str:
    """Najnowsza znana data odnowy (per kanał lub globalna)."""
    candidates: list[str] = []
    if isinstance(entry, dict):
        for key in ("renewed_at", "checked_at"):
            v = str(entry.get(key) or "").strip()
            if v:
                candidates.append(v)
    root = str(raw.get("token_renewed_at") or raw.get("renewed_at") or "").strip()
    if root:
        candidates.append(root)
    if not candidates:
        return ""
    return max(candidates)


def _estimate_days_from_renewal(raw: dict, entry: dict | None = None) -> int | None:
    iso = _latest_renewal_iso(raw, entry)
    if not iso:
        return None
    return _estimate_days_from_checked(iso)


def analyze_meta_tokens(*, live_debug: bool = True) -> MetaTokenReport:
    """Analizuje 4 kanaly — najkrotszy pozostaly czas w days_left_min."""
    raw = _read_raw_creds()
    creds = load_meta_credentials()
    seen_tokens: dict[str, dict] = {}
    report = MetaTokenReport()
    notes: list[str] = []

    for ch in _cp.all_channels():
        entry = creds.get(ch.code) or {}
        token = (entry.get("access_token") or "").strip()
        has_id = bool(entry.get("page_id") or entry.get("ig_user_id"))
        configured = bool(token and has_id)

        if not configured:
            report.channels.append(
                ChannelTokenStatus(
                    channel_code=ch.code,
                    label=ch.label,
                    configured=False,
                    is_valid=None,
                    expires_at=None,
                    days_left=None,
                    detail="Brak tokenu lub ID w meta_credentials.json",
                )
            )
            report.any_missing = True
            continue

        if token not in seen_tokens and live_debug:
            seen_tokens[token] = debug_access_token(token)

        data = seen_tokens.get(token, {})
        is_valid = data.get("is_valid") if data else None
        expires_at = _expires_unix(data) if data else None
        days_left = _days_left_from_expires(expires_at)

        raw_entry = raw.get(ch.code) if isinstance(raw.get(ch.code), dict) else {}
        if days_left is None and isinstance(raw_entry, dict):
            stored_exp = raw_entry.get("expires_at")
            try:
                if stored_exp not in (None, "", "0"):
                    expires_at = int(stored_exp)
            except (TypeError, ValueError):
                pass
            days_left = _days_left_from_expires(expires_at)
            if days_left is None:
                est = _estimate_days_from_renewal(raw, raw_entry)
                if est is not None:
                    days_left = est

        is_page_token = expires_at == 0 or (data.get("type") == "PAGE" if data else False)
        if days_left is not None:
            detail = (
                f"Pozostało {days_left} dni (od odnowy)"
                if is_page_token or expires_at in (None, 0)
                else f"Pozostało {days_left} dni"
            )
        elif is_page_token and (is_valid is True or is_valid is None):
            detail = "Token strony — bez daty wygaśnięcia (OK)"
        elif is_valid is False:
            detail = "Token nieważny"
        else:
            detail = "Nie udało się odczytać daty — odnów tokeny"

        if is_valid is False or (days_left is not None and days_left <= 0):
            report.any_expired = True

        report.channels.append(
            ChannelTokenStatus(
                channel_code=ch.code,
                label=ch.label,
                configured=True,
                is_valid=is_valid if isinstance(is_valid, bool) else None,
                expires_at=expires_at,
                days_left=days_left,
                detail=detail,
            )
        )

    left_values = [c.days_left for c in report.channels if c.days_left is not None]
    if left_values:
        report.days_left_min = min(left_values)
    elif report.any_expired:
        report.days_left_min = 0
    else:
        root_est = _estimate_days_from_renewal(raw)
        if root_est is not None:
            report.days_left_min = root_est

    app_id, _ = meta_app_credentials()
    if not app_id:
        notes.append("META_APP_ID + META_APP_SECRET w .env — dokładniejszy debug_token")
    elif report.days_left_min is not None and any(
        c.detail.startswith("Pozostało") and "od odnowy" in c.detail for c in report.channels
    ):
        notes.append(f"Page tokeny: odliczanie {DEFAULT_TOKEN_LIFETIME_DAYS} dni od daty odnowy")

    report.note = " · ".join(dict.fromkeys(notes))
    return report


def refresh_token_metadata_in_file(*, mark_renewed: bool = False) -> None:
    """Po zapisie tokenow — aktualizuje expires_at / checked_at / renewed_at w pliku creds."""
    raw = _read_raw_creds()
    if not raw:
        return
    changed = False
    seen: dict[str, dict] = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if mark_renewed:
        raw["token_renewed_at"] = now
        changed = True
    elif not raw.get("token_renewed_at"):
        backfill = _latest_renewal_iso(raw)
        if backfill:
            raw["token_renewed_at"] = backfill
            changed = True
    for code in _cp.CHANNEL_ORDER:
        entry = raw.get(code)
        if not isinstance(entry, dict):
            continue
        token = str(entry.get("access_token") or "").strip()
        if not token:
            continue
        if token not in seen:
            seen[token] = debug_access_token(token)
        data = seen[token]
        exp = _expires_unix(data)
        entry["checked_at"] = now
        if mark_renewed:
            entry["renewed_at"] = now
        elif not entry.get("renewed_at") and entry.get("checked_at"):
            entry["renewed_at"] = str(entry["checked_at"])
        if exp is not None:
            entry["expires_at"] = str(exp)
        if "is_valid" in data:
            entry["is_valid"] = str(bool(data.get("is_valid"))).lower()
        raw[code] = entry
        changed = True
    if changed:
        _CREDS_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")


def status_label_and_color(report: MetaTokenReport) -> tuple[str, str]:
    if report.any_missing:
        return "Brak konfiguracji", "#888"
    if report.any_expired:
        return "Wygasły", "#c62828"
    if report.days_left_min is not None:
        if report.days_left_min <= 7:
            return "Uwaga", "#f57f17"
        if report.days_left_min <= 14:
            return "Odśwież wkrótce", "#fb8c00"
        return "OK", "#2e7d32"
    return "Info", "#666"
