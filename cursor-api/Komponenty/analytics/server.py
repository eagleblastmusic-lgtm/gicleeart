"""Serwer HTTP — collect + API dashboardu + statyczne pliki web."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
import signal
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_COMPONENT_DIR = Path(__file__).resolve().parent
_CURSOR_API = _COMPONENT_DIR.parents[1]
_WEB_DIR = _COMPONENT_DIR / "web"
_PIXEL_DIR = _COMPONENT_DIR / "pixel"

if str(_CURSOR_API) not in sys.path:
    sys.path.insert(0, str(_CURSOR_API))

from Komponenty.analytics import aggregations, collect, storage  # noqa: E402
from Komponenty.analytics.collect import CollectError, ingest_event, make_test_event  # noqa: E402
from Komponenty.analytics.env_config import (  # noqa: E402
    auto_sync_interval_seconds,
    collect_public_url,
    collect_secret,
    effective_collect_url,
    server_port,
    worker_base_url,
)
from Komponenty.analytics.privacy import verify_collect_secret  # noqa: E402
from Komponenty.analytics import settings as analytics_settings  # noqa: E402
from Komponenty.analytics.shopify_sync import ShopifySyncError, sync_orders  # noqa: E402
from Komponenty.analytics.worker_sync import WorkerSyncError, pull_from_worker, worker_stats, purge_worker_d1  # noqa: E402
from Komponenty.analytics.pixel_snippet import build_pixel_snippet  # noqa: E402

API_VERSION = 2

_server: ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None
_sync_stop: threading.Event | None = None
_sync_thread: threading.Thread | None = None


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _cors_preflight(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(HTTPStatus.NO_CONTENT)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-Analytics-Secret")
    handler.end_headers()


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length > 65536:
        raise CollectError("Payload too large", 413)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise CollectError("Invalid JSON", 400) from exc
    if not isinstance(data, dict):
        raise CollectError("JSON object required", 400)
    return data


def _qs(handler: BaseHTTPRequestHandler) -> dict[str, list[str]]:
    return parse_qs(urlparse(handler.path).query)


def _qs_one(handler: BaseHTTPRequestHandler, key: str, default: str = "") -> str:
    vals = _qs(handler).get(key) or []
    return vals[0] if vals else default


def _segment_filters(handler: BaseHTTPRequestHandler) -> dict[str, str | None]:
    return {
        "country": _qs_one(handler, "country") or None,
        "device": _qs_one(handler, "device") or None,
        "source": _qs_one(handler, "source") or None,
    }
def _date_range_from_request(handler: BaseHTTPRequestHandler) -> tuple[str, str, str, str]:
    preset = _qs_one(handler, "preset", "7d")
    date_from = _qs_one(handler, "from") or None
    date_to = _qs_one(handler, "to") or None
    return aggregations.parse_date_range(preset, date_from, date_to)


def _serve_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    if not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND)
        return
    data = path.read_bytes()
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    if path.suffix in {".html", ".js", ".css"}:
        handler.send_header("Cache-Control", "no-cache, must-revalidate")
    handler.end_headers()
    handler.wfile.write(data)


class AnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "GicleeAnalytics/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        pass

    def do_OPTIONS(self) -> None:
        _cors_preflight(self)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path in ("/", "/dashboard", "/analiza-ruchu"):
            return _serve_file(self, _WEB_DIR / "index.html")

        if path.startswith("/web/"):
            rel = path[len("/web/") :]
            return _serve_file(self, _WEB_DIR / rel)

        if path == "/pixel/giclee-analytics-pixel.js":
            return _serve_file(self, _PIXEL_DIR / "giclee-analytics-pixel.js")

        if path == "/api/analytics/health":
            return _json_response(self, {
                "ok": True,
                "api_version": API_VERSION,
                "stats": storage.stats_summary(),
            })

        if path == "/api/analytics/status":
            worker = {}
            try:
                worker = worker_stats()
            except Exception as exc:
                worker = {"ok": False, "error": str(exc)}
            collect_url = effective_collect_url(server_port())
            local_url = f"http://127.0.0.1:{server_port()}/api/analytics/collect"
            local_stats = storage.stats_summary()
            last_sync = analytics_settings.get_last_sync()
            pixel_ok = bool(worker.get("ok") and worker.get("last_event_at"))
            return _json_response(self, {
                "api_version": API_VERSION,
                "collect_secret_configured": bool(collect_secret()),
                "collect_url": collect_url,
                "local_collect_url": local_url,
                "is_production_collect": "127.0.0.1" not in collect_url,
                "worker": worker,
                "stats": local_stats,
                "cloud_events": worker.get("total_events"),
                "local_events": local_stats.get("total_events"),
                "last_worker_sync_at": last_sync,
                "pixel_connected": pixel_ok,
                "pixel_last_event_at": worker.get("last_event_at"),
                "auto_sync_interval_seconds": auto_sync_interval_seconds(),
                "settings": analytics_settings.get_settings(),
                "exclusion_impact": storage.count_exclusion_impact(),
                "recent_visitors": storage.suggest_recent_visitors(),
            })

        if path == "/api/analytics/settings":
            if self._local_only():
                return _json_response(self, analytics_settings.get_settings())
            return _json_response(self, {
                "utm_templates": analytics_settings.get_settings().get("utm_templates"),
                "exclude_visitor_hashes": [],
                "exclude_ip_hashes": [],
            })

        if path == "/api/analytics/utm-preview":
            from Komponenty.analytics.env_config import allowed_shop_domain

            tpl = {
                "utm_source": _qs_one(self, "utm_source", "instagram"),
                "utm_medium": _qs_one(self, "utm_medium", "social"),
                "utm_campaign": _qs_one(self, "utm_campaign", "launch"),
                "path": _qs_one(self, "path", "/products/"),
            }
            url = analytics_settings.build_utm_url(
                base_domain=allowed_shop_domain(),
                **tpl,
            )
            return _json_response(self, {"url": url, **tpl})

        if path == "/api/analytics/pixel-snippet" and self._local_only():
            return _json_response(self, {
                "collect_url": effective_collect_url(server_port()),
                "snippet": build_pixel_snippet(port=server_port()),
            })

        if path == "/api/analytics/pixel-config":
            return _json_response(self, {
                "collect_url": collect_public_url() or f"http://127.0.0.1:{server_port()}/api/analytics/collect",
                "shop_domain": collect_public_url(),
            })

        api_routes = {
            "/api/analytics/overview": self._api_overview,
            "/api/analytics/countries": self._api_countries,
            "/api/analytics/funnel": self._api_funnel,
            "/api/analytics/products": self._api_products,
            "/api/analytics/sources": self._api_sources,
            "/api/analytics/realtime": self._api_realtime,
            "/api/analytics/sessions": self._api_sessions,
            "/api/analytics/timeline": self._api_timeline,
            "/api/analytics/insights": self._api_insights,
            "/api/analytics/frame-funnel": self._api_frame_funnel,
            "/api/analytics/export": self._api_export,
        }
        handler_fn = api_routes.get(path)
        if handler_fn:
            return handler_fn()
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/")

        if path == "/api/analytics/collect":
            return self._post_collect()
        if path == "/api/analytics/test-event":
            return self._post_test_event()
        if path == "/api/analytics/sync-shopify":
            return self._post_sync_shopify()
        if path == "/api/analytics/pull-worker":
            return self._post_pull_worker()
        if path == "/api/analytics/settings":
            return self._post_settings()
        if path == "/api/analytics/rebuild-sessions":
            return self._post_rebuild_sessions()
        if path == "/api/analytics/purge-worker":
            return self._post_purge_worker()
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        if path != "/api/analytics/delete":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        secret = self.headers.get("X-Analytics-Secret") or ""
        if not verify_collect_secret(secret, collect_secret()):
            return _json_response(self, {"error": "Unauthorized"}, 401)
        visitor = _qs_one(self, "visitor_id_hash")
        session = _qs_one(self, "session_id")
        date_from = _qs_one(self, "from")
        date_to = _qs_one(self, "to")
        result = storage.delete_analytics(
            visitor_id_hash=visitor or None,
            session_id=session or None,
            date_from=date_from or None,
            date_to=date_to or None,
        )
        _json_response(self, {"ok": True, "deleted": result})

    def _headers_dict(self) -> dict[str, str]:
        return {k: v for k, v in self.headers.items()}

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0] if self.client_address else ""

    def _post_collect(self) -> None:
        try:
            data = _read_json(self)
            result = ingest_event(
                data,
                headers=self._headers_dict(),
                client_ip=self._client_ip(),
            )
            _json_response(self, result)
        except CollectError as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, exc.status)

    def _post_test_event(self) -> None:
        secret = self.headers.get("X-Analytics-Secret") or ""
        local = self.client_address[0] in ("127.0.0.1", "::1")
        if not local and not verify_collect_secret(secret, collect_secret()):
            return _json_response(self, {"error": "Unauthorized"}, 401)
        try:
            data = make_test_event()
            result = ingest_event(data, headers=self._headers_dict())
            _json_response(self, result)
        except CollectError as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, exc.status)

    def _post_sync_shopify(self) -> None:
        if not self._local_only():
            return _json_response(self, {"error": "Unauthorized"}, 401)
        days = int(_qs_one(self, "days", "365") or "365")
        try:
            result = sync_orders(days_back=days)
            _json_response(self, {"ok": True, **result})
        except ShopifySyncError as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, 400)
        except Exception as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, 500)

    def _post_pull_worker(self) -> None:
        if not self._local_only():
            return _json_response(self, {"error": "Unauthorized"}, 401)
        since = _qs_one(self, "since") or None
        try:
            result = pull_from_worker(since=since or None)
            _json_response(self, {"ok": True, **result})
        except WorkerSyncError as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, 502)

    def _post_settings(self) -> None:
        if not self._local_only():
            return _json_response(self, {"error": "Unauthorized"}, 401)
        try:
            data = _read_json(self)
        except CollectError as exc:
            return _json_response(self, {"ok": False, "error": str(exc)}, exc.status)
        action = str(data.get("action") or "save")
        if action == "exclude":
            try:
                saved = analytics_settings.add_exclusion(
                    visitor_id=str(data.get("visitor_id") or ""),
                    ip=str(data.get("ip") or ""),
                    visitor_hash=str(data.get("visitor_hash") or ""),
                )
            except ValueError as exc:
                return _json_response(self, {"ok": False, "error": str(exc)}, 400)
            return _json_response(self, {"ok": True, "settings": saved})
        if action == "toggle_my_ip":
            try:
                saved = analytics_settings.toggle_my_ip(
                    ip=str(data.get("ip") or ""),
                    enabled=bool(data.get("enabled", True)),
                )
            except ValueError as exc:
                return _json_response(self, {"ok": False, "error": str(exc)}, 400)
            return _json_response(self, {"ok": True, "settings": saved})
        if action == "remove_exclusion":
            try:
                saved = analytics_settings.remove_exclusion(
                    kind=str(data.get("kind") or ""),
                    hash_value=str(data.get("hash") or ""),
                )
            except ValueError as exc:
                return _json_response(self, {"ok": False, "error": str(exc)}, 400)
            return _json_response(self, {"ok": True, "settings": saved})
        saved = analytics_settings.save_settings(data)
        _json_response(self, {"ok": True, "settings": saved})

    def _post_rebuild_sessions(self) -> None:
        if not self._local_only():
            return _json_response(self, {"error": "Unauthorized"}, 401)
        from Komponenty.analytics import sessions as sess_mod

        since = _qs_one(self, "since") or None
        count = sess_mod.rebuild_sessions(since=since)
        _json_response(self, {"ok": True, "sessions_rebuilt": count})

    def _post_purge_worker(self) -> None:
        if not self._local_only():
            return _json_response(self, {"error": "Unauthorized"}, 401)
        days = int(_qs_one(self, "days", "90") or "90")
        try:
            result = purge_worker_d1(days=days)
            _json_response(self, {"ok": True, **result})
        except WorkerSyncError as exc:
            _json_response(self, {"ok": False, "error": str(exc)}, 502)

    def _local_only(self) -> bool:
        return self.client_address[0] in ("127.0.0.1", "::1")

    def _api_overview(self) -> None:
        df, dt, pdf, pdt = _date_range_from_request(self)
        seg = _segment_filters(self)
        current = aggregations.compute_overview(df, dt, **seg)
        previous = aggregations.compute_overview(pdf, pdt, **seg)
        timeline = aggregations.compute_timeline(df, dt, **seg)
        _json_response(self, {
            "range": {"from": df, "to": dt},
            "current": current,
            "previous": previous,
            "timeline": timeline,
        })

    def _api_countries(self) -> None:
        df, dt, _, _ = _date_range_from_request(self)
        _json_response(self, aggregations.compute_countries(df, dt))

    def _api_funnel(self) -> None:
        df, dt, pdf, pdt = _date_range_from_request(self)
        seg = _segment_filters(self)
        data = aggregations.compute_funnel_compare(df, dt, pdf, pdt, **seg)
        _json_response(self, data)

    def _api_products(self) -> None:
        df, dt, pdf, pdt = _date_range_from_request(self)
        seg = _segment_filters(self)
        data = aggregations.compute_products_compare(df, dt, pdf, pdt, **seg)
        _json_response(self, data)

    def _api_sources(self) -> None:
        df, dt, _, _ = _date_range_from_request(self)
        _json_response(self, aggregations.compute_sources(df, dt))

    def _api_realtime(self) -> None:
        minutes = int(_qs_one(self, "minutes", "15") or "15")
        _json_response(self, aggregations.compute_realtime(minutes=minutes))

    def _api_sessions(self) -> None:
        df, dt, _, _ = _date_range_from_request(self)
        sid = _qs_one(self, "session_id")
        if sid:
            _json_response(self, aggregations.session_timeline(sid))
            return
        sessions = storage.query_sessions(date_from=df, date_to=dt, limit=100)
        _json_response(self, {"sessions": sessions})

    def _api_timeline(self) -> None:
        df, dt, _, _ = _date_range_from_request(self)
        _json_response(self, {"timeline": aggregations.compute_timeline(df, dt)})

    def _api_insights(self) -> None:
        df, dt, pdf, pdt = _date_range_from_request(self)
        seg = _segment_filters(self)
        current = aggregations.compute_overview(df, dt, **seg)
        previous = aggregations.compute_overview(pdf, pdt, **seg)
        countries = aggregations.compute_countries(df, dt)
        products = aggregations.compute_products(df, dt, **seg)
        funnel = aggregations.compute_funnel(df, dt, **seg)
        insights = aggregations.compute_insights(current, previous, countries, products, funnel)
        _json_response(self, {"insights": insights})

    def _api_frame_funnel(self) -> None:
        df, dt, _, _ = _date_range_from_request(self)
        seg = _segment_filters(self)
        _json_response(self, aggregations.compute_frame_funnel(df, dt, **seg))

    def _api_export(self) -> None:
        fmt = _qs_one(self, "format", "json")
        df, dt, _, _ = _date_range_from_request(self)
        seg = _segment_filters(self)
        if fmt == "weekly_report":
            report = aggregations.build_weekly_report(df, dt, **seg)
            if _qs_one(self, "download") == "1":
                lines = [
                    "GicleeArt — raport tygodniowy",
                    f"Wygenerowano: {report['generated_at']}",
                    f"Zakres: {report['range']['from']} — {report['range']['to']}",
                    "",
                    "=== KPI ===",
                    f"Sesje: {report['overview'].get('sessions', 0)}",
                    f"Unikalni: {report['overview'].get('visitors', 0)}",
                    f"Zakupy: {report['overview'].get('purchases', 0)}",
                    f"Przychód: {report['overview'].get('revenue', 0)} PLN",
                    f"Konwersja: {report['overview'].get('conversion_rate', 0):.2%}",
                    "",
                    "=== Top produkty ===",
                ]
                for p in report.get("top_products") or []:
                    lines.append(
                        f"- {p.get('product_title')}: {p.get('unique_viewers')} unikalnych, "
                        f"{p.get('views')} wyświetleń, {p.get('purchases')} zakupów"
                    )
                data = "\n".join(lines).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=raport_tygodniowy.txt")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            return _json_response(self, report)
        events = storage.query_events(date_from=df, date_to=dt, limit=50_000)
        if fmt == "csv":
            buf = io.StringIO()
            if events:
                writer = csv.DictWriter(buf, fieldnames=list(events[0].keys()))
                writer.writeheader()
                writer.writerows(events)
            data = buf.getvalue().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=analytics_events.csv")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        _json_response(self, {"events": events})


def _run_worker_sync_safe() -> dict[str, Any] | None:
    if not collect_secret() or not worker_base_url():
        return None
    try:
        return pull_from_worker()
    except WorkerSyncError:
        return None
    except Exception:
        return None


def _worker_sync_loop(stop: threading.Event, interval: int) -> None:
    _run_worker_sync_safe()
    while not stop.wait(interval):
        _run_worker_sync_safe()


def _start_auto_sync() -> None:
    global _sync_stop, _sync_thread
    if _sync_thread and _sync_thread.is_alive():
        return
    interval = auto_sync_interval_seconds()
    if interval <= 0:
        return
    _sync_stop = threading.Event()
    _sync_thread = threading.Thread(
        target=_worker_sync_loop,
        args=(_sync_stop, interval),
        daemon=True,
        name="analytics-worker-sync",
    )
    _sync_thread.start()


def _stop_auto_sync() -> None:
    global _sync_stop, _sync_thread
    if _sync_stop is not None:
        _sync_stop.set()
    _sync_stop = None
    _sync_thread = None


def _pids_listening_on_port(port: int) -> list[int]:
    """PID-y procesów nasłuchujących na porcie (bez bieżącego procesu)."""
    my_pid = os.getpid()
    found: list[int] = []
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                errors="replace",
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            return []
        needle = f":{port}"
        for line in out.splitlines():
            if "LISTENING" not in line or needle not in line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            pid_s = parts[-1]
            if not pid_s.isdigit():
                continue
            pid = int(pid_s)
            if pid and pid != my_pid:
                found.append(pid)
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                text=True,
                errors="replace",
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            return []
        for pid_s in out.split():
            if pid_s.isdigit():
                pid = int(pid_s)
                if pid != my_pid:
                    found.append(pid)
    return list(dict.fromkeys(found))


def _process_command_line(pid: int) -> str:
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/FORMAT:LIST"],
                text=True,
                errors="replace",
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            return ""
        for line in out.splitlines():
            if line.startswith("CommandLine="):
                return line.split("=", 1)[1].strip()
        return ""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", errors="replace")
        return cmdline.replace("\x00", " ").strip()
    except OSError:
        return ""


def _should_terminate_port_listener(pid: int) -> bool:
    cmd = _process_command_line(pid).lower()
    if not cmd:
        return False
    if "komponenty.analytics.server" in cmd or "komponenty.analytics" in cmd and ".server" in cmd:
        return True
    if "giclee_app" in cmd:
        return False
    return False


def _free_port_listeners(port: int) -> None:
    """Kończy stare procesy `python -m Komponenty.analytics.server` trzymające port."""
    for pid in _pids_listening_on_port(port):
        if not _should_terminate_port_listener(pid):
            continue
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    if any(_should_terminate_port_listener(pid) for pid in _pids_listening_on_port(port)):
        time.sleep(0.2)


def start_server(*, port: int | None = None, background: bool = True) -> str:
    """Uruchamia serwer analityki. Zwraca URL bazy."""
    global _server, _server_thread
    storage.init_db()
    p = port or server_port()
    url = f"http://127.0.0.1:{p}/"

    if _server is not None:
        return url

    _free_port_listeners(p)
    _server = ThreadingHTTPServer(("127.0.0.1", p), AnalyticsHandler)

    if background:
        _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _server_thread.start()
        _start_auto_sync()
    else:
        _start_auto_sync()
        _server.serve_forever()
    return url


def stop_server() -> None:
    global _server, _server_thread
    _stop_auto_sync()
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
        _server_thread = None


def restart_server(*, port: int | None = None, background: bool = True) -> str:
    """Zatrzymuje stary proces i uruchamia serwer z aktualnym kodem."""
    stop_server()
    return start_server(port=port, background=background)


def is_running() -> bool:
    return _server is not None


if __name__ == "__main__":
    storage.init_db()
    url = start_server(background=False, port=server_port())
    print(f"Analytics server: {url}")
