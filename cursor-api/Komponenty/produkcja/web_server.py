"""Prosty webowy serwer produkcji do uzytku na telefonie w warsztacie.

Cel: w warsztacie masz telefon w kieszeni. Zamiast podbiegac do komputera
zeby zaznaczyc "Ramka wycieta", wchodzisz na `http://<ip-twojego-kompa>:5000`
w przegladarce telefonu, logujesz sie tym samym haslem co GicleeApp, widzisz
liste zamowien i klikasz checkboxy. Zmiany trafiaja do `zamowienia.json`.

Uruchomienie:
    cd cursor-api
    python -m Komponenty.produkcja.web_server
    (albo przez skrot .cmd)

Serwer dziala tylko na LAN - sluchamy na 0.0.0.0:5000 co znaczy ze dostep
jest z kazdego urzadzenia w tej samej sieci WiFi (telefon, tablet).
NIE wystawiamy tego na internet bez dodatkowej konfiguracji - haslo PBKDF2
jest wystarczajace na LAN ale nie do publicznego routowania.

Technologia: czysta biblioteka standardowa Python (http.server + wsgiref).
Zero dependencies. Sesje na cookies (token 32 bajty w pamieci procesu).

Bezpieczenstwo:
- Haslo sprawdzane przez `Komponenty._shared.auth.verify_password`
  (ten sam hash co launcher).
- Bez hasla kazdy request dostaje 302 -> /login.
- Cookie `session=<token>` jest tylko w pamieci procesu -> restart = wylog
  wszystkich.
- CSRF: form-id w hidden input, porownywane z sesja.
"""

from __future__ import annotations

import html
import json
import secrets
import sys
import threading
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# Zeby import Komponenty._shared dzialal
_CURSOR_API = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_CURSOR_API))

from giclee_app.app_paths import atomic_write_text  # noqa: E402

from Komponenty._shared import auth  # noqa: E402
from Komponenty.produkcja import production_store  # noqa: E402
from Komponenty.produkcja import retention, shipping  # noqa: E402
from Komponenty.produkcja.frame_variant import migrate_order_frame_fields  # noqa: E402
from Komponenty.produkcja.shopify_links import admin_order_url  # noqa: E402

_LEGACY_DATA_DIR = _CURSOR_API / "Komponenty" / "produkcja" / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE
_SESSION_FILE = _CURSOR_API / ".shopify_session.json"


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    current_dir = Path(_DATA_DIR)
    if current_dir != _LEGACY_DATA_DIR:
        return current_dir / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()


def _session_shop_domain() -> str:
    try:
        if _SESSION_FILE.is_file():
            d = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
            return str(d.get("shop") or "")
    except (OSError, json.JSONDecodeError):
        pass
    return ""

# In-memory sesje (token -> meta)
_SESSIONS: dict[str, dict[str, Any]] = {}
_SESSIONS_LOCK = threading.Lock()
_SESSION_TTL_MIN = 720  # 12 godzin - potem trzeba sie ponownie zalogowac

_PAINT_CURE_SECONDS = 72 * 3600


# ============================================================================
# Data helpers
# ============================================================================


def _load_db() -> dict:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        db = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}
    for o in db.get("orders") or []:
        migrate_order_frame_fields(o)
    return db


def _save_db(db: dict) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\n",
    )


def _cure_remaining_seconds(order: dict) -> int:
    if order.get("pomin_schniecie"):
        return 0
    raw = order.get("data_pomalowania")
    if not raw:
        return 0
    try:
        start = datetime.fromisoformat(str(raw))
    except ValueError:
        return 0
    delta = start + timedelta(seconds=_PAINT_CURE_SECONDS) - datetime.now()
    return max(0, int(delta.total_seconds()))


def _format_countdown(seconds: int) -> str:
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if d > 0:
        return f"{d}d {h:02d}g {m:02d}m"
    if h > 0:
        return f"{h:02d}g {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


def _overall_status(o: dict) -> str:
    if o.get("wyslane"):
        return "Zrealizowane"
    if o.get("spakowane"):
        return "Gotowe do wysylki"
    if o.get("zlozone"):
        return "Do spakowania"
    wydruk_step = int(o.get("wydruk_step") or 0)
    ramka_step = int(o.get("ramka_step") or 0)
    ramka_cure = _cure_remaining_seconds(o) if ramka_step >= 4 else -1
    if wydruk_step >= 2 and ramka_step >= 4 and ramka_cure == 0:
        return "Do zlozenia"
    parts = []
    if wydruk_step < 2:
        parts.append(f"Wydruk {wydruk_step}/2")
    if ramka_step < 4:
        parts.append(f"Ramka {ramka_step}/4")
    elif ramka_cure > 0:
        parts.append(f"Utwardzanie {_format_countdown(ramka_cure)}")
    return " | ".join(parts) or "W produkcji"


# ============================================================================
# Auth / sessions
# ============================================================================


def _create_session() -> str:
    token = secrets.token_urlsafe(32)
    with _SESSIONS_LOCK:
        _SESSIONS[token] = {
            "created_at": datetime.now(),
            "csrf": secrets.token_urlsafe(16),
        }
    return token


def _get_session(token: str | None) -> dict | None:
    if not token:
        return None
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(token)
        if not sess:
            return None
        if datetime.now() - sess["created_at"] > timedelta(minutes=_SESSION_TTL_MIN):
            del _SESSIONS[token]
            return None
        return sess


def _destroy_session(token: str | None) -> None:
    if not token:
        return
    with _SESSIONS_LOCK:
        _SESSIONS.pop(token, None)


# ============================================================================
# HTML
# ============================================================================


def _html_page(title: str, body: str, *, extra_head: str = "") -> bytes:
    t = html.escape(title)
    content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t} - Produkcja GicleeArt</title>
{extra_head}
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, "Segoe UI", sans-serif;
         background: #f4f4f7; color: #222; }}
  header {{ background: #1565c0; color: white; padding: 12px 16px;
           display: flex; justify-content: space-between; align-items: center;
           position: sticky; top: 0; z-index: 10; box-shadow: 0 2px 4px rgba(0,0,0,0.15); }}
  header h1 {{ margin: 0; font-size: 18px; }}
  header a {{ color: white; text-decoration: none; font-size: 14px; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 12px; }}
  .card {{ background: white; border-radius: 8px; padding: 14px;
          margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .card h3 {{ margin: 0 0 6px 0; font-size: 16px; }}
  .card .meta {{ color: #666; font-size: 13px; margin-bottom: 6px; }}
  .status {{ display: inline-block; padding: 3px 8px; border-radius: 4px;
            font-size: 12px; font-weight: bold; }}
  .status.done {{ background: #c8e6c9; color: #2e7d32; }}
  .status.ready {{ background: #bbdefb; color: #0d47a1; }}
  .status.waiting {{ background: #fff8e1; color: #5d4037; }}
  .status.overdue {{ background: #ffcdd2; color: #b71c1c; }}
  .countdown {{ font-family: Consolas, monospace; font-size: 18px;
               font-weight: bold; padding: 8px; border-radius: 4px;
               color: white; text-align: center; margin: 8px 0; }}
  .countdown.red {{ background: #c62828; }}
  .countdown.orange {{ background: #ef6c00; }}
  .countdown.green {{ background: #43a047; }}
  .countdown.done {{ background: #2e7d32; }}
  .step-row {{ display: flex; align-items: center; padding: 8px;
              border-radius: 4px; margin: 4px 0;
              background: #fafafa; min-height: 44px; }}
  .step-row:hover {{ background: #f0f0f0; }}
  .step-row.checked {{ background: #e8f5e9; }}
  .step-row label {{ flex: 1; font-size: 15px; cursor: pointer; }}
  .step-row input[type="checkbox"] {{ transform: scale(1.4); margin-right: 12px; cursor: pointer; }}
  .progress {{ font-family: Consolas, monospace; font-size: 13px; }}
  form {{ margin: 0; }}
  button, input[type="submit"] {{ padding: 10px 16px; border: 0; border-radius: 4px;
           background: #1565c0; color: white; cursor: pointer; font-size: 15px; }}
  input[type="password"], input[type="text"] {{ padding: 10px; border: 1px solid #ddd;
                                                 border-radius: 4px; font-size: 15px; width: 100%; }}
  .btn-link {{ display: inline-block; text-decoration: none; background: #1565c0;
              color: white; padding: 8px 12px; border-radius: 4px; font-size: 14px; }}
  .btn-back {{ background: #666; }}
  section {{ margin-bottom: 20px; }}
  section h2 {{ font-size: 16px; color: #333; margin: 0 0 8px 0;
               padding-bottom: 4px; border-bottom: 2px solid #1565c0; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    return content.encode("utf-8")


def _render_login(error: str = "") -> bytes:
    err_html = f'<p style="color:red;margin-top:8px">{html.escape(error)}</p>' if error else ""
    body = f"""
<header>
  <h1>Produkcja - logowanie</h1>
</header>
<div class="container" style="max-width:420px;margin-top:32px">
  <div class="card">
    <h3>Zaloguj sie</h3>
    <p style="color:#666;font-size:14px">Uzyj tego samego hasla co w GicleeApp.</p>
    <form method="POST" action="/login">
      <input type="password" name="password" autofocus required
             placeholder="Haslo" autocomplete="current-password">
      <div style="margin-top:12px">
        <input type="submit" value="Zaloguj" style="width:100%">
      </div>
      {err_html}
    </form>
  </div>
</div>
"""
    return _html_page("Logowanie", body)


def _render_list(orders: list[dict]) -> bytes:
    # Filtrowanie: aktywne na gorze, zrealizowane na dole
    active = [o for o in orders if not o.get("wyslane")]
    done = [o for o in orders if o.get("wyslane")]
    active.sort(key=lambda x: (x.get("data_zamowienia", ""), x.get("id", "")), reverse=True)

    cards_html = []
    for o in active:
        status = _overall_status(o)
        status_class = "waiting"
        if o.get("spakowane"):
            status_class = "ready"
        cards_html.append(_render_order_card(o, status, status_class))
    if not cards_html:
        cards_html.append('<p style="color:#666;padding:20px;text-align:center">(brak aktywnych zamowien)</p>')

    done_html = []
    for o in sorted(done, key=lambda x: x.get("data_wyslania", ""), reverse=True)[:10]:
        done_html.append(_render_order_card(o, "Zrealizowane", "done"))

    body = f"""
<header>
  <h1>Produkcja</h1>
  <a href="/logout">Wyloguj</a>
</header>
<div class="container">
  <section>
    <h2>Aktywne ({len(active)})</h2>
    {''.join(cards_html)}
  </section>
  {'<section><h2>Ostatnie zrealizowane (10)</h2>' + ''.join(done_html) + '</section>' if done_html else ''}
</div>
"""
    return _html_page("Produkcja", body, extra_head='<meta http-equiv="refresh" content="60">')


def _render_order_card(o: dict, status: str, status_class: str) -> str:
    oid = html.escape(o.get("id", ""))
    client = html.escape(o.get("client") or "(bez klienta)")
    title = html.escape(o.get("tytul_obrazu") or "")
    dmk = html.escape(o.get("ramka_drewno") or "")
    rmk = html.escape(o.get("ramka_rozmiar") or "")
    kmk = html.escape(o.get("ramka_kolor") or "")
    ppk = html.escape(o.get("passepartout_kolor") or "")
    qty = o.get("ilosc", 1)
    img_html = ""
    siu = (o.get("shopify_image_url") or "").strip()
    if siu:
        img_html = (
            f'<div style="margin-top:6px"><img src="{html.escape(siu)}" alt="" '
            f'style="max-width:100%;max-height:100px;border-radius:6px;object-fit:contain"></div>'
        )
    adm = ""
    oidn = int(o.get("shopify_order_id") or 0)
    if oidn:
        dom = _session_shop_domain()
        if dom:
            adm = (
                f'<div class="meta"><a href="{html.escape(admin_order_url(dom, oidn))}">'
                f"Shopify Admin (zamowienie)</a></div>"
            )
    wydruk = int(o.get("wydruk_step") or 0)
    ramka = int(o.get("ramka_step") or 0)
    progress_str = f"Wydruk {wydruk}/2 · Ramka {ramka}/4"
    if o.get("zlozone"):
        progress_str += " · Zlozone"
    if o.get("spakowane"):
        progress_str += " · Spakowane"
    if o.get("wyslane"):
        progress_str += " · Wyslane"
    return f"""
<a href="/order/{oid}" style="text-decoration:none;color:inherit">
  <div class="card">
    <h3>{oid} - {client}</h3>
    <div class="meta">{title}</div>
    <div class="meta">Drewno: {dmk} · Rozmiar: {rmk} · Kolor: {kmk} · Passepartout: {ppk or "—"} · x{qty}</div>
    {adm}
    {img_html}
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
      <span class="progress">{progress_str}</span>
      <span class="status {status_class}">{html.escape(status)}</span>
    </div>
  </div>
</a>
"""


def _render_order_detail(o: dict, csrf: str, message: str = "") -> bytes:
    oid = html.escape(o.get("id", ""))
    client = html.escape(o.get("client") or "(bez klienta)")
    title = html.escape(o.get("tytul_obrazu") or "")
    dmk = html.escape(o.get("ramka_drewno") or "")
    rmk = html.escape(o.get("ramka_rozmiar") or "")
    kmk = html.escape(o.get("ramka_kolor") or "")
    ppk = html.escape(o.get("passepartout_kolor") or "")
    qty = o.get("ilosc", 1)
    shopify_no = html.escape(o.get("shopify_order_no", "") or "")
    adres = html.escape(o.get("adres_wysylki", "") or "")
    notatka = html.escape(o.get("notatka", "") or "")
    wydruk_step = int(o.get("wydruk_step") or 0)
    ramka_step = int(o.get("ramka_step") or 0)

    adm_html = ""
    oidn = int(o.get("shopify_order_id") or 0)
    if oidn:
        dom = _session_shop_domain()
        if dom:
            au = html.escape(admin_order_url(dom, oidn))
            adm_html = f'<div class="meta"><a href="{au}">Shopify Admin — to zamowienie</a></div>'
    img_d = ""
    siu = (o.get("shopify_image_url") or "").strip()
    if siu:
        img_d = (
            f'<div style="margin-top:8px"><img src="{html.escape(siu)}" alt="" '
            f'style="max-width:100%;max-height:220px;border-radius:8px;object-fit:contain"></div>'
        )

    # Countdown (jesli pomalowana)
    countdown_html = ""
    if ramka_step >= 4:
        remaining = _cure_remaining_seconds(o)
        if remaining > 0:
            if remaining < 24 * 3600:
                cls = "red"
            elif remaining < 48 * 3600:
                cls = "orange"
            else:
                cls = "green"
            countdown_html = (
                f'<div class="countdown {cls}" id="countdown" data-remaining="{remaining}">'
                f'Utwardzanie: <span id="countdown-text">{_format_countdown(remaining)}</span>'
                f'</div>'
            )
        else:
            countdown_html = '<div class="countdown done">Ramka utwardzona - gotowa do zlozenia</div>'

    # Message (toast po zmianie)
    msg_html = f'<div style="background:#c8e6c9;color:#2e7d32;padding:8px;border-radius:4px;margin-bottom:10px">{html.escape(message)}</div>' if message else ""

    # Rows generator
    def _step_row(name: str, label: str, checked: bool, disabled: bool = False) -> str:
        dis_attr = " disabled" if disabled else ""
        chk_attr = " checked" if checked else ""
        cls = "checked" if checked else ""
        return f"""
<form method="POST" action="/order/{oid}/toggle">
  <input type="hidden" name="csrf" value="{csrf}">
  <input type="hidden" name="step" value="{name}">
  <label class="step-row {cls}">
    <input type="checkbox" name="checked" value="1"{chk_attr}{dis_attr}
           onchange="this.form.submit()">
    {html.escape(label)}
  </label>
</form>
"""

    # Wydruk (steps 0-2 progressive)
    wydruk_rows = [
        _step_row("wydruk_1", "Po korekcji kolorystycznej", wydruk_step >= 1),
        _step_row("wydruk_2", "Wydrukowany", wydruk_step >= 2),
    ]

    # Ramka (steps 0-4 progressive)
    ramka_rows = [
        _step_row("ramka_1", "Drewno dostepne", ramka_step >= 1),
        _step_row("ramka_2", "Ramka wycieta", ramka_step >= 2),
        _step_row("ramka_3", "Ramka wyszlifowana", ramka_step >= 3),
        _step_row("ramka_4", "Ramka pomalowana (start 72h)", ramka_step >= 4),
    ]

    # Finalizacja
    wydruk_done = wydruk_step >= 2
    ramka_done = ramka_step >= 4 and _cure_remaining_seconds(o) == 0
    final_rows = [
        _step_row("zlozone", "Zlozone", bool(o.get("zlozone")),
                  disabled=not (wydruk_done and ramka_done)),
        _step_row("spakowane", "Spakowane", bool(o.get("spakowane")),
                  disabled=not o.get("zlozone")),
        _step_row("wyslane", "Wyslane", bool(o.get("wyslane")),
                  disabled=not o.get("spakowane")),
    ]

    body = f"""
<header>
  <h1>{oid}</h1>
  <a href="/">← Powrot</a>
</header>
<div class="container">
  {msg_html}
  <div class="card">
    <h3>{client}</h3>
    <div class="meta">{title}</div>
    <div class="meta">Drewno: {dmk} · Rozmiar: {rmk} · Kolor: {kmk} · Passepartout: {ppk or "—"} · x{qty}</div>
    {f'<div class="meta">Shopify: {shopify_no}</div>' if shopify_no else ''}
    {adm_html}
    {img_d}
  </div>

  {countdown_html}

  <section>
    <h2>Wydruk</h2>
    {''.join(wydruk_rows)}
  </section>

  <section>
    <h2>Ramka</h2>
    {''.join(ramka_rows)}
  </section>

  <section>
    <h2>Finalizacja</h2>
    {''.join(final_rows)}
  </section>

  {f'<div class="card"><h3>Adres wysylki</h3><pre style="white-space:pre-wrap;font-family:inherit;margin:0">{adres}</pre></div>' if adres else ''}
  {f'<div class="card"><h3>Notatka</h3><pre style="white-space:pre-wrap;font-family:inherit;margin:0">{notatka}</pre></div>' if notatka else ''}
</div>

<script>
// Live countdown JS
(function() {{
  var el = document.getElementById('countdown');
  if (!el) return;
  var remaining = parseInt(el.dataset.remaining, 10);
  var txt = document.getElementById('countdown-text');
  function tick() {{
    remaining--;
    if (remaining < 0) {{ window.location.reload(); return; }}
    var d = Math.floor(remaining / 86400);
    var h = Math.floor((remaining % 86400) / 3600);
    var m = Math.floor((remaining % 3600) / 60);
    var s = remaining % 60;
    var str;
    if (d > 0) str = d + 'd ' + String(h).padStart(2, '0') + 'g ' + String(m).padStart(2, '0') + 'm';
    else if (h > 0) str = String(h).padStart(2, '0') + 'g ' + String(m).padStart(2, '0') + 'm ' + String(s).padStart(2, '0') + 's';
    else str = String(m).padStart(2, '0') + 'm ' + String(s).padStart(2, '0') + 's';
    txt.textContent = str;
  }}
  setInterval(tick, 1000);
}})();
</script>
"""
    return _html_page(f"Zamowienie {oid}", body)


# ============================================================================
# Handlers
# ============================================================================


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "GicleeArt-Production/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Ograniczamy spam w konsoli - logujemy tylko bledy
        if args and isinstance(args[1], str) and args[1].startswith(("4", "5")):
            super().log_message(format, *args)

    def _get_session_token(self) -> str | None:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get("session")
        return morsel.value if morsel else None

    def _send(self, status: HTTPStatus, body: bytes,
              *, content_type: str = "text/html; charset=utf-8",
              cookie: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, *, cookie: str | None = None) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _require_login(self) -> dict | None:
        token = self._get_session_token()
        sess = _get_session(token)
        if sess is None:
            self._redirect("/login")
            return None
        return sess

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        path = url.path

        if path == "/login":
            self._send(HTTPStatus.OK, _render_login())
            return

        if path == "/logout":
            token = self._get_session_token()
            _destroy_session(token)
            self._redirect("/login", cookie="session=; Path=/; Max-Age=0")
            return

        sess = self._require_login()
        if sess is None:
            return

        if path == "/" or path == "":
            db = _load_db()
            self._send(HTTPStatus.OK, _render_list(db.get("orders") or []))
            return

        if path.startswith("/order/"):
            parts = path.split("/", 3)
            if len(parts) < 3:
                self._send(HTTPStatus.NOT_FOUND, b"Not found", content_type="text/plain")
                return
            order_id = parts[2]
            db = _load_db()
            order = next((o for o in db.get("orders") or [] if o.get("id") == order_id), None)
            if not order:
                self._send(HTTPStatus.NOT_FOUND, b"Zamowienie nie znalezione", content_type="text/plain")
                return
            # Message from query string (po toggle)
            qs = parse_qs(url.query)
            msg = (qs.get("msg") or [""])[0]
            self._send(HTTPStatus.OK, _render_order_detail(order, sess["csrf"], message=msg))
            return

        self._send(HTTPStatus.NOT_FOUND, b"Not found", content_type="text/plain")

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        path = url.path
        length = int(self.headers.get("Content-Length") or 0)
        body_bytes = self.rfile.read(length) if length > 0 else b""
        form = {k: v[0] for k, v in parse_qs(body_bytes.decode("utf-8")).items()}

        if path == "/login":
            password = form.get("password", "")
            if not auth.is_configured():
                self._send(HTTPStatus.OK, _render_login(
                    "Haslo nie jest jeszcze ustawione. Uruchom najpierw GicleeApp."
                ))
                return
            if not auth.verify_password(password):
                self._send(HTTPStatus.OK, _render_login("Bledne haslo."))
                return
            token = _create_session()
            cookie = f"session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={_SESSION_TTL_MIN * 60}"
            self._redirect("/", cookie=cookie)
            return

        sess = self._require_login()
        if sess is None:
            return

        if path.startswith("/order/") and path.endswith("/toggle"):
            # CSRF check
            if form.get("csrf") != sess["csrf"]:
                self._send(HTTPStatus.FORBIDDEN, b"CSRF", content_type="text/plain")
                return
            order_id = path.split("/", 3)[2]
            step = form.get("step", "")
            checked = form.get("checked") == "1"
            msg = self._toggle_step(order_id, step, checked)
            from urllib.parse import quote
            self._redirect(f"/order/{order_id}?msg={quote(msg)}")
            return

        self._send(HTTPStatus.NOT_FOUND, b"Not found", content_type="text/plain")

    def _toggle_step(self, order_id: str, step: str, checked: bool) -> str:
        db = _load_db()
        order = next((o for o in db.get("orders") or [] if o.get("id") == order_id), None)
        if not order:
            return "Zamowienie nie znalezione"

        # Wydruk (wydruk_1, wydruk_2)
        if step.startswith("wydruk_"):
            target = int(step.split("_")[1])
            cur = int(order.get("wydruk_step") or 0)
            new_step = max(cur, target) if checked else min(cur, target - 1)
            order["wydruk_step"] = max(0, min(2, new_step))
            _save_db(db)
            return f"Wydruk krok {target}: {'OK' if checked else 'cofniety'}"

        # Ramka (ramka_1..4)
        if step.startswith("ramka_"):
            target = int(step.split("_")[1])
            cur = int(order.get("ramka_step") or 0)
            new_step = max(cur, target) if checked else min(cur, target - 1)
            new_step = max(0, min(4, new_step))
            prev_painted = cur >= 4
            new_painted = new_step >= 4
            if new_painted and not prev_painted:
                order["data_pomalowania"] = datetime.now().isoformat(timespec="seconds")
            elif not new_painted and prev_painted:
                order["data_pomalowania"] = None
            order["ramka_step"] = new_step
            _save_db(db)
            return f"Ramka krok {target}: {'OK' if checked else 'cofniety'}"

        # Finalizacja
        if step in ("zlozone", "spakowane", "wyslane"):
            order[step] = checked
            if step == "zlozone" and not checked:
                order["spakowane"] = False
                order["wyslane"] = False
                order["data_wyslania"] = None
            if step == "spakowane" and not checked:
                order["wyslane"] = False
                order["data_wyslania"] = None
            if step == "wyslane":
                order["data_wyslania"] = date.today().isoformat() if checked else None
            _save_db(db)
            return f"{step.capitalize()}: {'OK' if checked else 'cofniety'}"

        return "Nieznany krok"


# ============================================================================
# Server
# ============================================================================


def run_server(*, host: str = "0.0.0.0", port: int = 5000) -> None:
    print(f"[produkcja.web] Startuje serwer na http://{host}:{port}/")
    print(f"[produkcja.web] Z telefonu w tej samej sieci WiFi: http://<IP-komputera>:{port}/")
    print(f"[produkcja.web] Zaloguj sie tym samym haslem co GicleeApp.")
    print(f"[produkcja.web] Ctrl+C zatrzymuje serwer.")
    if not auth.is_configured():
        print("[produkcja.web] UWAGA: haslo nie jest ustawione. Uruchom GicleeApp")
        print("  albo 'python set_password.py' zeby je ustawic.")
    server = ThreadingHTTPServer((host, port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[produkcja.web] Zatrzymuje serwer...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Webowy serwer produkcji")
    parser.add_argument("--host", default="0.0.0.0", help="Adres (domyslnie 0.0.0.0 = LAN)")
    parser.add_argument("--port", type=int, default=5000, help="Port (domyslnie 5000)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
