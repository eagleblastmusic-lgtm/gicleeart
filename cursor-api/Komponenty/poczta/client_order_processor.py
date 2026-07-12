"""Pobieranie plików zamówień „Własna fotografia” z maili Workera (linki R2)."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from giclee_app.app_paths import atomic_write_text, data_path

from .env_config import client_orders_base_dir
from .imap_client import fetch_message_html

USER_AGENT = "GicleeApp/1.0 (poczta-zamowienia)"
_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_DATA_DIR = _LEGACY_DATA_DIR
_PROCESSED_FILE = _LEGACY_DATA_DIR / "processed_client_orders.json"
_PROCESSED = data_path("Komponenty/poczta/data/processed_client_orders.json", legacy=_PROCESSED_FILE)


def _processed_path(*, for_write: bool) -> Path:
    if Path(_PROCESSED_FILE) != _LEGACY_DATA_DIR / "processed_client_orders.json":
        return Path(_PROCESSED_FILE)
    return _PROCESSED.write_path if for_write else _PROCESSED.read_path()

# Windows nie pozwala na „:” w nazwie folderu — używamy wariantu bez dwukropka.
_FOLDER_PREFIX = "Numer zamówienia"


@dataclass
class ParsedClientOrderItem:
    index: int
    upload_id: str
    product_title: str
    quantity: int
    frame_lines: list[str]
    original_url: str
    preview_url: str
    crop_url: str
    meta_url: str


@dataclass
class ParsedClientOrder:
    order_number: str
    folder_name: str
    customer_name: str
    customer_email: str
    shopify_id: str
    items: list[ParsedClientOrderItem]


@dataclass
class ProcessResult:
    uid: str
    ok: bool
    folder: Path | None = None
    message: str = ""


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text_parts: list[str] = []
        self._in_a = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._in_a = True
            self._href = ""
            self._text_parts = []
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self._href = v.strip()
                    break

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_a:
            text = re.sub(r"\s+", " ", "".join(self._text_parts)).strip()
            if self._href:
                self.links.append((self._href, text))
            self._in_a = False

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text_parts.append(data)


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)</p>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def is_custom_photo_order_subject(subject: str) -> bool:
    s = _normalize(subject)
    return "własna fotografia" in s or "wlasna fotografia" in s


def _extract_order_number(html: str, subject: str) -> str:
    for pattern in (
        r"Numer\s+zamówienia:\s*(#[0-9]+)",
        r"Numer\s+zamowienia:\s*(#[0-9]+)",
        r"zamówienie\s+(#[0-9]+)",
        r"zamowienie\s+(#[0-9]+)",
    ):
        m = re.search(pattern, html + " " + subject, re.IGNORECASE)
        if m:
            return m.group(1)
    m = re.search(r"(#[0-9]{3,})", subject)
    return m.group(1) if m else ""


def _folder_name_for_order(order_number: str) -> str:
    num = order_number.strip() or "#?"
    if not num.startswith("#"):
        num = f"#{num}"
    return f"{_FOLDER_PREFIX} {num}"


def _pick_link(links: list[tuple[str, str]], *keywords: str) -> str:
    for url, label in links:
        lab = _normalize(label)
        for kw in keywords:
            if _normalize(kw) in lab:
                return url
    return ""


def _pick_meta_link(links: list[tuple[str, str]]) -> str:
    for url, label in links:
        if label.strip().lower() == "meta.json" or url.rstrip("/").endswith("/meta.json"):
            return url
    return ""


def _pick_original_link(links: list[tuple[str, str]]) -> str:
    for url, label in links:
        lab = _normalize(label)
        if "oryginał zdjęcia" in lab or "oryginal zdjecia" in lab or lab.startswith("📷"):
            return url
    return ""


def _split_product_blocks(html: str) -> list[str]:
    """Dzieli HTML maila na bloki produktów (Worker oddziela pozycje tagiem hr)."""
    parts = re.split(r"(?is)<hr\b[^>]*>", html)
    blocks = [p for p in parts[1:] if re.search(r"(?i)upload\s+id:|podgl[aą]d\s+mockupu|orygina", p)]
    if blocks:
        return blocks
    if re.search(r"(?i)upload\s+id:", html):
        return [html]
    return []


def _parse_product_block(block_html: str) -> ParsedClientOrderItem | None:
    plain = _strip_html(block_html)
    parser = _LinkParser()
    try:
        parser.feed(block_html)
    except Exception:
        pass
    links = parser.links

    upload_id = ""
    m_up = re.search(r"Upload ID:\s*([0-9a-f-]{36})", plain, re.IGNORECASE)
    if m_up:
        upload_id = m_up.group(1)

    product_title = ""
    m_t = re.search(r"(?:^|\n)([^\n]+)\nIlość:", plain)
    if m_t:
        product_title = m_t.group(1).strip()

    quantity = 1
    m_q = re.search(r"Ilość:\s*([0-9]+)", plain, re.IGNORECASE)
    if m_q:
        quantity = max(1, int(m_q.group(1)))

    frame_lines: list[str] = []
    frame_block = re.search(r"Ramka\s*(.*?)(?:Pliki|Upload ID)", plain, re.IGNORECASE | re.DOTALL)
    if frame_block:
        for line in frame_block.group(1).splitlines():
            line = line.strip()
            if line:
                frame_lines.append(line)

    original_url = _pick_original_link(links)
    preview_url = _pick_link(links, "podgląd mockupu", "podglad mockupu")
    crop_url = _pick_link(links, "dane kadrowania")
    meta_url = _pick_meta_link(links)

    if not any((original_url, preview_url, crop_url, meta_url)):
        return None

    return ParsedClientOrderItem(
        index=0,
        upload_id=upload_id,
        product_title=product_title or "Własna fotografia",
        quantity=quantity,
        frame_lines=frame_lines,
        original_url=original_url,
        preview_url=preview_url,
        crop_url=crop_url,
        meta_url=meta_url,
    )


def parse_order_email(html: str, subject: str) -> ParsedClientOrder | None:
    if not is_custom_photo_order_subject(subject):
        return None
    plain = _strip_html(html)
    if "własna fotografia" not in _normalize(plain) and "nowe zamówienie" not in _normalize(plain):
        if not is_custom_photo_order_subject(subject):
            return None

    order_number = _extract_order_number(html, subject)
    if not order_number:
        return None

    customer_name = ""
    customer_email = ""
    m_c = re.search(r"Klient:\s*([^\n<]+)", plain, re.IGNORECASE)
    if m_c:
        customer_name = m_c.group(1).strip()
    m_e = re.search(r"E-mail:\s*([^\s\n<]+)", plain, re.IGNORECASE)
    if m_e:
        customer_email = m_e.group(1).strip()

    shopify_id = ""
    m_id = re.search(r"ID Shopify:\s*([0-9]+)", plain, re.IGNORECASE)
    if m_id:
        shopify_id = m_id.group(1)

    items: list[ParsedClientOrderItem] = []
    for block_html in _split_product_blocks(html):
        item = _parse_product_block(block_html)
        if item is not None:
            items.append(item)

    if not items:
        return None

    for i, item in enumerate(items, start=1):
        item.index = i

    return ParsedClientOrder(
        order_number=order_number,
        folder_name=_folder_name_for_order(order_number),
        customer_name=customer_name,
        customer_email=customer_email,
        shopify_id=shopify_id,
        items=items,
    )


def _guess_ext(url: str, default: str) -> str:
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"jpg", "jpeg", "png", "webp", "heic", "json"}:
        return "jpg" if suffix == "jpeg" else suffix
    return default


def _apply_index_suffix(name: str, index: int, total: int) -> str:
    if total <= 1:
        return name
    p = Path(name)
    return f"{p.stem}_{index}{p.suffix}"


def _build_download_plan(order: ParsedClientOrder) -> list[tuple[str, str, str]]:
    downloads: list[tuple[str, str, str]] = []
    total = len(order.items)
    for item in order.items:
        idx = item.index
        if item.original_url:
            ext = _guess_ext(item.original_url, "jpg")
            fname = _apply_index_suffix(f"Oryginał zdjęcia klienta.{ext}", idx, total)
            downloads.append((item.original_url, fname, f"oryginał {idx}"))
        if item.preview_url:
            ext = _guess_ext(item.preview_url, "jpg")
            fname = _apply_index_suffix(f"Podgląd mockupu.{ext}", idx, total)
            downloads.append((item.preview_url, fname, f"podgląd {idx}"))
        if item.crop_url:
            fname = _apply_index_suffix("Dane kadrowania.json", idx, total)
            downloads.append((item.crop_url, fname, f"kadrowanie {idx}"))
        if item.meta_url:
            fname = _apply_index_suffix("meta.json", idx, total)
            downloads.append((item.meta_url, fname, f"meta {idx}"))
    return downloads


def _file_on_disk(folder: Path, fname: str) -> bool:
    path = folder / fname
    if path.is_file() and path.stat().st_size > 0:
        return True
    if fname.startswith("Oryginał"):
        stem = Path(fname).stem
        return any(p.is_file() and p.stat().st_size > 0 for p in folder.glob(f"{stem}.*"))
    return False


def _folder_is_complete(folder: Path, order: ParsedClientOrder) -> bool:
    if not folder.is_dir():
        return False
    for _url, fname, _label in _build_download_plan(order):
        if not _file_on_disk(folder, fname):
            return False
    meta = folder / "dane_klienta.txt"
    return meta.is_file() and meta.stat().st_size > 0


def _normalize_original_to_jpg(folder: Path, fname: str) -> str:
    """Lightroom addPhoto nie obsługuje WEBP/HEIC — zapisujemy zawsze jako JPG."""
    path = folder / fname
    if not fname.startswith("Oryginał"):
        return fname
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return fname
    if ext not in {".webp", ".heic", ".heif", ".png"}:
        return fname
    try:
        from PIL import Image
    except ImportError:
        return fname
    dest = folder / f"{path.stem}.jpg"
    try:
        with Image.open(path) as img:
            img.convert("RGB").save(dest, quality=95)
        if dest.resolve() != path.resolve():
            path.unlink(missing_ok=True)
        return dest.name
    except OSError:
        return fname


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=180) as resp:
        data = resp.read()
    dest.write_bytes(data)


def _build_client_txt(order: ParsedClientOrder) -> str:
    lines = [
        f"Numer zamówienia: {order.order_number}",
        f"Data pobrania: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "KLIENT",
        f"Imię i nazwisko: {order.customer_name or '(brak)'}",
        f"E-mail: {order.customer_email or '(brak)'}",
        "",
    ]
    if order.shopify_id:
        lines.append(f"ID Shopify: {order.shopify_id}")
        lines.append("")

    total = len(order.items)
    for item in order.items:
        heading = f"ZAMÓWIENIE — pozycja {item.index}/{total}" if total > 1 else "ZAMÓWIENIE"
        lines.append(heading)
        lines.append(f"Produkt: {item.product_title}")
        lines.append(f"Ilość: {item.quantity}")
        if item.upload_id:
            lines.append(f"Upload ID: {item.upload_id}")
        if item.frame_lines:
            lines.append("")
            lines.append("RAMKA")
            lines.extend(item.frame_lines)
        lines.append("")
        lines.append("PLIKI (pobrane z R2)")
        if item.original_url:
            lines.append(f"- Oryginał zdjęcia klienta: {item.original_url}")
        if item.preview_url:
            lines.append(f"- Podgląd mockupu: {item.preview_url}")
        if item.crop_url:
            lines.append(f"- Dane kadrowania: {item.crop_url}")
        if item.meta_url:
            lines.append(f"- meta.json: {item.meta_url}")
        if item.index < total:
            lines.extend(["", "—" * 40, ""])

    return "\n".join(lines) + "\n"


def _load_processed() -> dict[str, object]:
    path = _processed_path(for_write=False)
    if not path.is_file():
        return {"uids": [], "orders": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"uids": [], "orders": {}}
    if not isinstance(raw, dict):
        return {"uids": [], "orders": {}}
    raw.setdefault("uids", [])
    raw.setdefault("orders", {})
    return raw


def _save_processed(data: dict[str, object]) -> None:
    atomic_write_text(_processed_path(for_write=True), json.dumps(data, indent=2, ensure_ascii=False))


def is_uid_processed(uid: str) -> bool:
    data = _load_processed()
    uids = data.get("uids")
    return isinstance(uids, list) and uid in uids


def process_message(uid: str, subject: str, *, base_dir: Path | None = None) -> ProcessResult:
    """Parsuje mail, tworzy folder klienta i pobiera pliki z linków R2."""
    try:
        html = fetch_message_html(uid)
    except Exception as exc:
        return ProcessResult(uid=uid, ok=False, message=f"Nie można odczytać maila: {exc}")

    order = parse_order_email(html, subject)
    if order is None:
        return ProcessResult(uid=uid, ok=False, message="Nie rozpoznano zamówienia własnej fotografii")

    root = base_dir or client_orders_base_dir()
    folder = root / order.folder_name
    if _folder_is_complete(folder, order):
        _mark_processed(uid, order.order_number, str(folder))
        return ProcessResult(
            uid=uid,
            ok=True,
            folder=folder,
            message="Już przetworzone",
        )

    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    errors: list[str] = []

    for url, fname, label in _build_download_plan(order):
        try:
            if _file_on_disk(folder, fname):
                saved.append(fname)
                continue
            _download_file(url, folder / fname)
            if label.startswith("oryginał"):
                fname = _normalize_original_to_jpg(folder, fname)
            saved.append(fname)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{label}: {exc}")

    try:
        (folder / "dane_klienta.txt").write_text(_build_client_txt(order), encoding="utf-8")
        saved.append("dane_klienta.txt")
    except OSError as exc:
        errors.append(f"dane_klienta.txt: {exc}")

    if not saved or (len(saved) == 1 and saved == ["dane_klienta.txt"] and errors):
        return ProcessResult(
            uid=uid,
            ok=False,
            folder=folder,
            message="Nie pobrano plików: " + "; ".join(errors),
        )

    _mark_processed(uid, order.order_number, str(folder))
    msg = f"Zapisano w {folder}"
    if errors:
        msg += f" (częściowo: {'; '.join(errors)})"
    return ProcessResult(uid=uid, ok=True, folder=folder, message=msg)


def _mark_processed(uid: str, order_number: str, folder: str) -> None:
    data = _load_processed()
    uids = data.get("uids")
    if not isinstance(uids, list):
        uids = []
    if uid not in uids:
        uids.append(uid)
    data["uids"] = uids[-500:]
    orders = data.get("orders")
    if not isinstance(orders, dict):
        orders = {}
    orders[order_number] = {
        "uid": uid,
        "folder": folder,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data["orders"] = orders
    _save_processed(data)


def scan_and_process_inbox(
    messages: list,
    *,
    base_dir: Path | None = None,
) -> list[ProcessResult]:
    """Przetwarza nowe maile z tematem „własna fotografia” (lista MailMessage)."""
    results: list[ProcessResult] = []
    for msg in messages:
        subj = getattr(msg, "subject", "") or ""
        uid = getattr(msg, "uid", "") or ""
        if not uid or not is_custom_photo_order_subject(subj):
            continue
        results.append(process_message(uid, subj, base_dir=base_dir))
    return results
