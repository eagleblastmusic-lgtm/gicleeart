"""Nagrywanie przez OBS Studio (WebSocket v5) → docs/review-demos/."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import GptConfig
from .record import (
    VIDEO_SUFFIXES,
    import_manual_review_videos,
    purge_review_demo_videos,
    resolve_record_url,
)

DEFAULT_OBS_EXECUTABLE = Path(r"C:\Program Files\obs-studio\bin\64bit\obs64.exe")
OBS_WS_CONFIG_REL = Path("obs-studio") / "plugin_config" / "obs-websocket" / "config.json"
OBS_CONNECT_TIMEOUT = 5.0
OBS_LAUNCH_WAIT_SECONDS = 45.0
OBS_FILE_FLUSH_WAIT_SECONDS = 12.0
OBS_RECORD_START_ATTEMPTS = 12
OBS_RECORD_START_DELAY = 1.5


@dataclass
class ObsWebSocketSettings:
    host: str
    port: int
    password: str | None
    server_enabled: bool
    auth_required: bool
    config_path: Path | None = None
    password_source: str = "none"


@dataclass
class ObsRecordStartResult:
    ok: bool
    message: str = ""
    record_directory: Path | None = None
    preview_url: str = ""


@dataclass
class ObsRecordStopResult:
    ok: bool
    message: str = ""
    source_path: Path | None = None
    review_demo_path: Path | None = None


@dataclass
class _ActiveObsSession:
    record_directory: Path
    started_at: float


_active_session: _ActiveObsSession | None = None


def obs_recording_active() -> bool:
    return _active_session is not None


def _obs_ws_config_path() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        return Path()
    return Path(appdata) / OBS_WS_CONFIG_REL


def load_obs_websocket_settings(cfg: GptConfig) -> ObsWebSocketSettings:
    """Port/hasło z GUI, z fallbackiem do config.json OBS (AppData)."""
    config_path = _obs_ws_config_path()
    file_port = 4455
    file_password = ""
    server_enabled = True
    auth_required = False

    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_port = int(data.get("server_port") or 4455)
                file_password = str(data.get("server_password") or "")
                server_enabled = bool(data.get("server_enabled", False))
                auth_required = bool(data.get("auth_required", False))
        except (OSError, ValueError, TypeError):
            pass

    gui_password = (cfg.obs_websocket_password or "").strip()
    gui_port = int(cfg.obs_websocket_port or 0)
    port = file_port if gui_port <= 0 else gui_port
    if gui_password:
        password: str | None = gui_password
        password_source = "gui"
    elif file_password:
        password = file_password
        password_source = "obs_config"
    else:
        password = None
        password_source = "none"

    return ObsWebSocketSettings(
        host=cfg.obs_websocket_host or "127.0.0.1",
        port=port,
        password=password,
        server_enabled=server_enabled,
        auth_required=auth_required,
        config_path=config_path if config_path.is_file() else None,
        password_source=password_source,
    )


def enable_obs_websocket_server(*, log: list[str] | None = None) -> bool:
    """Włącza server_enabled w config OBS (gdy OBS jeszcze nie działa)."""
    lines = log if log is not None else []
    path = _obs_ws_config_path()
    if not path.is_file():
        lines.append("Brak config OBS WebSocket — w OBS włącz: Ustawienia → WebSocket.")
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        if data.get("server_enabled"):
            return False
        data["server_enabled"] = True
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        lines.append("Włączono OBS WebSocket w pliku konfiguracji (server_enabled=true).")
        return True
    except OSError as exc:
        lines.append(f"Nie udało się zapisać config OBS WebSocket: {exc}")
        return False


def is_obs_process_running() -> bool:
    if os.name != "nt":
        return False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return "obs64.exe" in (proc.stdout or "").lower()
    except OSError:
        return False


def _websocket_error_hint(ws: ObsWebSocketSettings, *, last_error: str = "") -> str:
    lines = [
        "Nie udało się połączyć z OBS WebSocket.",
        f"Port: {ws.port}, host: {ws.host}.",
    ]
    if not ws.server_enabled:
        lines.append(
            "WebSocket jest WYŁĄCZONY w OBS (server_enabled=false).\n"
            "W OBS: Ustawienia → WebSocket → włącz «Włącz WebSocket server».\n"
            "Albo zamknij OBS całkowicie i kliknij «Nagraj (OBS)» ponownie — aplikacja "
            "włączy WebSocket automatycznie przed startem."
        )
    elif ws.auth_required and ws.password_source == "none":
        lines.append(
            "OBS wymaga hasła WebSocket — wpisz je w polu «OBS WebSocket» w GUI\n"
            "albo ustaw w OBS: Ustawienia → WebSocket → hasło."
        )
    elif ws.password_source == "obs_config":
        lines.append("Hasło pobrane z config OBS — jeśli błąd auth, wpisz aktualne hasło w GUI.")
    else:
        lines.append(
            "Sprawdź: OBS 28+ → Ustawienia → WebSocket (włączony, port "
            f"{ws.port}). Hasło w polu «OBS WebSocket»."
        )
    if is_obs_process_running() and not ws.server_enabled:
        lines.append("OBS jest uruchomiony ze starym configiem — zamknij OBS i spróbuj ponownie.")
    if last_error:
        lines.append(f"Ostatni błąd: {last_error}")
    return "\n".join(lines)


def _obs_executable(cfg: GptConfig) -> Path:
    raw = (cfg.obs_executable or "").strip()
    return Path(raw) if raw else DEFAULT_OBS_EXECUTABLE


def _connect_client(ws: ObsWebSocketSettings):
    try:
        from obsws_python import ReqClient
    except ImportError as exc:
        raise RuntimeError(
            "Brak pakietu obsws-python.\n"
            "Uruchom: pip install obsws-python"
        ) from exc

    return ReqClient(
        host=ws.host,
        port=ws.port,
        password=ws.password,
        timeout=OBS_CONNECT_TIMEOUT,
    )


def _connect_client_for_cfg(cfg: GptConfig):
    ws = load_obs_websocket_settings(cfg)
    return _connect_client(ws), ws


def _disconnect_client(client) -> None:
    try:
        client.disconnect()
    except Exception:  # noqa: BLE001 — best-effort cleanup
        pass


def _websocket_ready(cfg: GptConfig) -> tuple[bool, ObsWebSocketSettings, str]:
    ws = load_obs_websocket_settings(cfg)
    if not ws.server_enabled:
        return False, ws, "server_disabled"
    client = None
    last_err = ""
    try:
        client = _connect_client(ws)
        return True, ws, ""
    except Exception as exc:  # noqa: BLE001 — diagnostyka połączenia
        last_err = str(exc)
        return False, ws, last_err
    finally:
        if client is not None:
            _disconnect_client(client)


def _launch_obs(cfg: GptConfig, *, start_recording: bool = False) -> None:
    exe = _obs_executable(cfg)
    if not exe.is_file():
        raise FileNotFoundError(
            f"Nie znaleziono OBS: {exe}\n"
            "Ustaw ścieżkę w data/gpt_config.json → obs_executable."
        )
    cmd = [str(exe)]
    if start_recording:
        cmd.append("--startrecording")
    subprocess.Popen(  # noqa: S603 — jawna ścieżka z konfiguracji użytkownika
        cmd,
        cwd=str(exe.parent),
    )


def _recording_is_active(client) -> bool:
    status = client.get_record_status()
    return bool(
        getattr(status, "output_active", False)
        or getattr(status, "outputActive", False)
    )


def _wait_for_websocket(cfg: GptConfig, *, log: list[str]) -> None:
    deadline = time.monotonic() + OBS_LAUNCH_WAIT_SECONDS
    last_ws = load_obs_websocket_settings(cfg)
    last_err = ""
    while time.monotonic() < deadline:
        time.sleep(1.0)
        ready, ws, err = _websocket_ready(cfg)
        last_ws = ws
        last_err = err
        if ready:
            if ws.password_source == "obs_config":
                log.append("OBS WebSocket: hasło z config OBS.")
            log.append("OBS WebSocket: gotowy.")
            return
        if err == "server_disabled":
            log.append("Czekam… WebSocket w OBS nadal wyłączony (restart OBS?).")
        elif err and err != last_err:
            log.append(f"Czekam na WebSocket… ({err[:120]})")
    raise RuntimeError(_websocket_error_hint(last_ws, last_error=last_err))


def ensure_obs_websocket(cfg: GptConfig, *, log: list[str] | None = None) -> bool:
    """Uruchamia OBS jeśli trzeba i czeka na WebSocket. Zwraca True gdy OBS dopiero uruchomiono."""
    lines = log if log is not None else []
    ready, ws, err = _websocket_ready(cfg)
    if ready:
        lines.append("OBS WebSocket: połączono.")
        return False

    if ws.server_enabled is False and is_obs_process_running():
        raise RuntimeError(_websocket_error_hint(ws, last_error=err))

    if ws.server_enabled is False:
        enable_obs_websocket_server(log=lines)

    lines.append("OBS WebSocket niedostępny — uruchamiam OBS z auto-nagrywaniem…")
    purge_review_demo_videos(log=lines)
    if not is_obs_process_running():
        _launch_obs(cfg, start_recording=True)
    else:
        lines.append("OBS już działa — czekam na WebSocket (może wymagać restartu OBS).")
    _wait_for_websocket(cfg, log=lines)
    return True


def _ensure_recording_started(client, log: list[str]) -> None:
    """StartRecord + weryfikacja; fallback toggle/hotkey gdy OBS dopiero wstał."""
    if _recording_is_active(client):
        log.append("OBS: nagrywanie już aktywne.")
        return

    last_err: Exception | None = None
    for attempt in range(1, OBS_RECORD_START_ATTEMPTS + 1):
        try:
            client.start_record()
            log.append(f"OBS: StartRecord (próba {attempt})")
        except Exception as exc:  # noqa: BLE001 — retry przy starcie OBS
            last_err = exc
            log.append(f"OBS StartRecord błąd (próba {attempt}): {exc}")
        time.sleep(OBS_RECORD_START_DELAY)
        if _recording_is_active(client):
            log.append("OBS: nagrywanie potwierdzone.")
            return

    for label, action in (
        ("ToggleRecord", lambda: client.toggle_record()),
        ("hotkey StartRecording", lambda: client.trigger_hotkey_by_name("OBSBasic.StartRecording")),
    ):
        try:
            action()
            log.append(f"OBS: fallback {label}")
        except Exception as exc:  # noqa: BLE001 — kolejny fallback
            log.append(f"OBS fallback {label}: {exc}")
        time.sleep(1.0)
        if _recording_is_active(client):
            log.append("OBS: nagrywanie potwierdzone (fallback).")
            return

    msg = (
        "OBS się uruchomił, ale nagrywanie nie wystartowało.\n"
        "Sprawdź w OBS: Wyjście → Nagrywanie (format/ścieżka), aktywna scena, WebSocket."
    )
    if last_err:
        msg += f"\nOstatni błąd StartRecord: {last_err}"
    raise RuntimeError(msg)


def _record_directory(client) -> Path:
    resp = client.get_record_directory()
    raw = getattr(resp, "record_directory", None) or getattr(resp, "recordDirectory", "")
    if not raw:
        raise RuntimeError("OBS nie zwrócił katalogu nagrań (GetRecordDirectory).")
    path = Path(str(raw))
    if not path.is_dir():
        raise RuntimeError(f"Katalog nagrań OBS nie istnieje: {path}")
    return path


def find_newest_recording(
    record_dir: Path,
    *,
    since: float | None = None,
) -> Path | None:
    """Najnowszy plik wideo w katalogu nagrań OBS."""
    candidates: list[Path] = []
    for path in record_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        if since is not None and path.stat().st_mtime < since - 2.0:
            continue
        candidates.append(path)
    if not candidates and since is not None:
        for path in record_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
                candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def wait_for_recording_file(
    record_dir: Path,
    *,
    since: float,
    timeout: float = OBS_FILE_FLUSH_WAIT_SECONDS,
) -> Path | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = find_newest_recording(record_dir, since=since)
        if found is not None:
            size1 = found.stat().st_size
            time.sleep(0.5)
            if found.is_file() and found.stat().st_size == size1 and size1 > 0:
                return found
        time.sleep(0.5)
    return find_newest_recording(record_dir, since=since)


def start_obs_recording(
    cfg: GptConfig,
    *,
    prefer_local: bool = True,
    log: list[str] | None = None,
) -> ObsRecordStartResult:
    global _active_session  # noqa: PLW0603 — stan sesji między start/stop w GUI

    lines = log if log is not None else []
    if _active_session is not None:
        return ObsRecordStartResult(ok=False, message="Nagrywanie OBS już trwa — użyj «Zatrzymaj (OBS)».")

    url, err = resolve_record_url(prefer_local=prefer_local)
    if err and prefer_local:
        return ObsRecordStartResult(ok=False, message=err)
    lines.append(f"Podgląd do nagrania: {url}")

    cold_start = ensure_obs_websocket(cfg, log=lines)

    client, _ws = _connect_client_for_cfg(cfg)
    try:
        if _recording_is_active(client) and not cold_start:
            return ObsRecordStartResult(
                ok=False,
                message="OBS już nagrywa (poza Integracją GPT). Zatrzymaj nagranie w OBS i spróbuj ponownie.",
            )

        record_dir = _record_directory(client)
        recording_already_active = _recording_is_active(client)
        if cold_start and recording_already_active:
            lines.append("OBS: auto-nagrywanie (--startrecording) aktywne.")
            started_at = time.time() - 120
        else:
            removed_review = purge_review_demo_videos(log=lines)
            if removed_review:
                lines.append(
                    f"Poprzednie nagrania usunięte z review-demos ({removed_review})."
                )
            _ensure_recording_started(client, lines)
            started_at = time.time()

        if not _recording_is_active(client):
            return ObsRecordStartResult(ok=False, message="OBS nie nagrywa — sprawdź log.")

        _active_session = _ActiveObsSession(record_directory=record_dir, started_at=started_at)
        lines.append(f"OBS: nagrywanie → {record_dir}")
        return ObsRecordStartResult(
            ok=True,
            message="OK",
            record_directory=record_dir,
            preview_url=url,
        )
    except Exception as exc:
        return ObsRecordStartResult(ok=False, message=str(exc))
    finally:
        _disconnect_client(client)


def stop_obs_recording(
    cfg: GptConfig,
    *,
    log: list[str] | None = None,
) -> ObsRecordStopResult:
    global _active_session  # noqa: PLW0603

    lines = log if log is not None else []
    session = _active_session
    if session is None:
        return ObsRecordStopResult(ok=False, message="Brak aktywnego nagrywania OBS.")

    client, _ws = _connect_client_for_cfg(cfg)
    try:
        status = client.get_record_status()
        if getattr(status, "output_active", False) or getattr(status, "outputActive", False):
            client.stop_record()
            lines.append("OBS: StopRecord")
        else:
            lines.append("OBS: nagrywanie już zatrzymane — szukam pliku…")
    finally:
        _disconnect_client(client)

    _active_session = None

    source = wait_for_recording_file(
        session.record_directory,
        since=session.started_at,
    )
    if source is None:
        return ObsRecordStopResult(
            ok=False,
            message=(
                f"Nagranie zatrzymane, ale nie znaleziono pliku wideo w:\n{session.record_directory}"
            ),
        )

    lines.append(f"Plik OBS: {source}")
    copied = import_manual_review_videos(source, log=lines)
    dest = copied.get("desktop")
    lines.append(f"Review demo: {dest}")
    try:
        source.unlink(missing_ok=True)
        lines.append(f"Usunięto plik tymczasowy OBS: {source.name}")
    except OSError as exc:
        lines.append(f"Uwaga: nie usunięto pliku OBS ({exc})")
    return ObsRecordStopResult(
        ok=True,
        message="OK",
        source_path=source,
        review_demo_path=dest,
    )
