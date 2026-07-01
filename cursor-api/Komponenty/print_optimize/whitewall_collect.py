"""Zbieranie par oryginal / Whitewall pcStrength przez Playwright + imageserver."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from PIL import Image

IMAGE_SERVER_BASE = "https://imageserver.whitewall.com/imageserver/image/view"
DEFAULT_PRODUCT = "item-acrylglasversieglung"
DEFAULT_LOCALE = "eu"
STRENGTHS = (0, 70, 100)
WW_MIN_EDGE = 700
_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif", ".tif", ".tiff"}

_ID_RE = re.compile(r"[?&]id=([^&]+)")


LogFn = Callable[[str], None] | None


@dataclass
class PairManifest:
    source_file: str
    image_id: str
    strengths: dict[str, str]
    original_url: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_imageserver_url(image_id: str, strength: int, *, token: str = "") -> str:
    qid = quote(image_id, safe="")
    url = f"{IMAGE_SERVER_BASE}?id={qid}&type=12&"
    if strength > 0:
        url += f"pcEnabled=on&pcStrength={int(strength)}&"
    if token:
        url += f"token={quote(token, safe='')}"
    return url.rstrip("&")


def parse_image_id(url: str) -> str:
    m = _ID_RE.search(url or "")
    if not m:
        raise ValueError(f"Nie znaleziono parametru id w URL: {url[:120]}")
    return m.group(1)


def download_via_request(request, url: str, dest: Path, *, timeout_ms: int = 120_000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = request.get(url, timeout=timeout_ms)
    if resp.status != 200:
        raise RuntimeError(f"HTTP {resp.status} dla {url[:100]}")
    data = resp.body()
    if not data:
        raise RuntimeError(f"Pusta odpowiedz: {url[:100]}")
    dest.write_bytes(data)


def download_url(url: str, dest: Path, timeout: float = 120.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "GicleePrintOptimize/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} dla {url[:100]}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc)) from exc
    if not data:
        raise RuntimeError(f"Pusta odpowiedz: {url[:100]}")
    dest.write_bytes(data)


def _image_size(src: Path) -> tuple[int, int]:
    with Image.open(src) as im:
        return im.size


def _validate_whitewall_size(width: int, height: int, *, label: str) -> None:
    if width >= WW_MIN_EDGE and height >= WW_MIN_EDGE:
        return
    raise ValueError(
        f"{label}: {width}x{height} px — Whitewall wymaga min. {WW_MIN_EDGE}x{WW_MIN_EDGE} px "
        "(obie krawedzie). Uzyj wiekszego pliku zrodlowego."
    )


def _prepare_upload_file(src: Path, temp_dir: Path) -> tuple[Path, Path]:
    """Zawsze konwertuj do JPG przed uploadem — najpewniejszy format dla Whitewall."""
    width, height = _image_size(src)
    _validate_whitewall_size(width, height, label=src.name)
    temp_dir.mkdir(parents=True, exist_ok=True)
    dest = temp_dir / f"{src.stem}_wwupload.jpg"
    try:
        Image.open(src).convert("RGB").save(dest, quality=92)
    except OSError as exc:
        raise ValueError(
            f"Nie mozna odczytac obrazu {src.name} ({exc}). "
            "Zapisz jako JPG i sprobuj ponownie."
        ) from exc
    return dest, dest


def _is_upload_configure(body: dict[str, Any]) -> bool:
    """Configure po udanym uploadzie — ma originalUrl i motifId."""
    if not (body.get("originalUrl") or body.get("url")):
        return False
    return bool(body.get("motifId"))


def _matches_enhancement(body: dict[str, Any], enhancement: int) -> bool:
    preview = body.get("url") or ""
    if not preview:
        return False
    if enhancement == 0:
        return "pcStrength" not in preview and "pcEnabled" not in preview
    if enhancement == 70:
        return "pcStrength=70" in preview
    if enhancement == 100:
        return "pcStrength=100" in preview
    strength = (body.get("imageEnhancement") or {}).get("strength")
    return strength == enhancement


def _dismiss_cookie_banner(page, timeout_ms: int) -> None:
    for sel in (
        "#onetrust-accept-btn-handler",
        'button:has-text("Accept all")',
        'button:has-text("Alle akzeptieren")',
    ):
        btn = page.locator(sel).first
        if not btn.count():
            continue
        try:
            btn.click(timeout=min(timeout_ms, 5000))
            page.wait_for_timeout(500)
            return
        except Exception:
            continue


def _configurator_url(*, product: str, locale: str) -> str:
    return (
        f"https://www.whitewall.com/{locale}/configurator"
        f"?product={product}&enhancement=70&formatType=FORMAT_INDIVIDUAL"
    )


def _wait_configurator_ready(page, timeout_ms: int) -> None:
    page.locator('[data-test="sidebar-container"]').wait_for(state="visible", timeout=timeout_ms)
    mask = page.locator("#swap-loading-mask")
    if mask.count():
        try:
            mask.wait_for(state="hidden", timeout=min(timeout_ms, 90_000))
        except Exception:
            pass
    page.wait_for_timeout(800)


def _open_select_photo_panel(page, *, timeout_ms: int, log: LogFn) -> Any:
    """Otwiera panel SELECT PHOTO i zwraca ukryty input[type=file]."""
    select_photo = page.locator(
        'li[data-test="sidebar-panel-option"]:has-text("SELECT PHOTO"), '
        '[data-test="Select photo"]'
    ).first
    select_photo.wait_for(state="visible", timeout=timeout_ms)
    file_input = page.locator('input[type="file"]').first
    panel_timeout = min(timeout_ms, 25_000)
    last_err: Exception | None = None

    for attempt in range(1, 4):
        try:
            select_photo.click(timeout=15_000, force=True)
            page.wait_for_timeout(2500)
            file_input.wait_for(state="attached", timeout=panel_timeout)
            return file_input
        except Exception as exc:
            last_err = exc
            if log:
                log(f"  panel SELECT PHOTO — proba {attempt}/3...")
            page.wait_for_timeout(1500)

    raise RuntimeError(f"Nie udalo sie otworzyc panelu SELECT PHOTO: {last_err}")


def _upload_via_configurator(
    page,
    upload_path: Path,
    *,
    product: str,
    locale: str,
    timeout_ms: int,
    log: LogFn,
) -> dict[str, Any]:
    """Otwiera panel SELECT PHOTO i wysyla plik przez oficjalny drop-zone Whitewall."""
    url = _configurator_url(product=product, locale=locale)
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    _wait_configurator_ready(page, timeout_ms)
    _dismiss_cookie_banner(page, timeout_ms)

    file_input = _open_select_photo_panel(page, timeout_ms=timeout_ms, log=log)

    captured: dict[str, Any] = {}
    register_status: dict[str, str | None] = {"status": None}

    def on_response(response) -> None:
        req_url = response.url
        if "/jsonApi/motif/registerMotif" in req_url:
            try:
                body = response.json()
                register_status["status"] = str(body.get("actionStatus") or "")
            except Exception:
                pass
            return
        if "/jsonApi/product/configure" not in req_url:
            return
        try:
            body = response.json()
        except Exception:
            return
        if _is_upload_configure(body):
            captured["configure"] = body

    page.on("response", on_response)
    try:
        captured.clear()
        register_status["status"] = None
        file_input.set_input_files(str(upload_path.resolve()))
        if log:
            log("  upload wyslany, czekam na registerMotif + configure...")

        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            if captured.get("configure"):
                return captured["configure"]
            page.wait_for_timeout(500)

        reg = register_status["status"] or "brak"
        try:
            w, h = _image_size(upload_path)
            size_hint = f" ({w}x{h} px)"
        except OSError:
            size_hint = ""
        raise TimeoutError(
            f"Brak odpowiedzi configure po uploadzie «{upload_path.name}»{size_hint}. "
            f"registerMotif={reg}. "
            f"Whitewall wymaga min. {WW_MIN_EDGE}x{WW_MIN_EDGE} px i stabilnego polaczenia."
        )
    finally:
        page.remove_listener("response", on_response)


def _wait_configure_at_enhancement(
    page,
    enhancement: int,
    *,
    timeout_ms: int,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def on_response(response) -> None:
        if "/jsonApi/product/configure" not in response.url:
            return
        try:
            body = response.json()
        except Exception:
            return
        if not (body.get("originalUrl") or body.get("url")):
            return
        if _matches_enhancement(body, enhancement):
            captured["configure"] = body

    page.on("response", on_response)
    try:
        parsed = urlparse(page.url)
        qs = parse_qs(parsed.query)
        qs["enhancement"] = [str(int(enhancement))]
        next_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
        page.goto(next_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2000)
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            if "configure" in captured:
                return captured["configure"]
            page.wait_for_timeout(500)
        raise TimeoutError(f"Brak odpowiedzi configure dla enhancement={enhancement}.")
    finally:
        page.remove_listener("response", on_response)


def collect_pairs_for_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    product: str = DEFAULT_PRODUCT,
    locale: str = DEFAULT_LOCALE,
    strengths: tuple[int, ...] = STRENGTHS,
    headless: bool = True,
    timeout_ms: int = 120_000,
    on_log: LogFn = None,
) -> list[PairManifest]:
    """Upload kazdego pliku do konfiguratora Whitewall i zapisuje pary JPEG."""
    def log(msg: str) -> None:
        if on_log:
            on_log(msg)
        else:
            print(msg)

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "collect-pairs wymaga playwright: pip install playwright && playwright install chromium"
        ) from exc

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_SUFFIXES
    )
    if not files:
        raise FileNotFoundError(f"Brak obrazow w {input_dir}")

    skipped: list[dict[str, str]] = []
    eligible: list[Path] = []
    for src in files:
        try:
            w, h = _image_size(src)
            _validate_whitewall_size(w, h, label=src.name)
            eligible.append(src)
        except ValueError as exc:
            skipped.append({"file": src.name, "reason": str(exc)})

    if skipped:
        log(f"Preflight: {len(skipped)} plikow za male (< {WW_MIN_EDGE}px) — pomijam.")
        for row in skipped[:8]:
            log(f"  pominiety: {row['file']} — {row['reason'][:90]}")
        if len(skipped) > 8:
            log(f"  ... i {len(skipped) - 8} kolejnych")

    if not eligible:
        raise ValueError(
            f"Zaden plik nie spelnia wymagan Whitewall (min. {WW_MIN_EDGE}x{WW_MIN_EDGE} px). "
            f"Wrzuc wieksze zdjecia do {input_dir}."
        )

    log(f"Do uploadu: {len(eligible)} plikow (z {len(files)} w folderze).")

    manifests: list[PairManifest] = []
    failed: list[dict[str, str]] = []
    temp_dir = output_dir / "_upload_tmp"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)

        for idx, src in enumerate(eligible, start=1):
            log(f"[{idx}/{len(eligible)}] Upload: {src.name}")
            upload_path: Path | None = None
            temp_path: Path | None = None
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()
            try:
                upload_path, temp_path = _prepare_upload_file(src, temp_dir)
                log("  przygotowano JPG dla Whitewall")

                cfg70 = _upload_via_configurator(
                    page,
                    upload_path,
                    product=product,
                    locale=locale,
                    timeout_ms=timeout_ms,
                    log=log,
                )

                original_url = cfg70.get("originalUrl") or cfg70.get("url") or ""
                image_id = parse_image_id(original_url)

                cfg0 = _wait_configure_at_enhancement(page, 0, timeout_ms=timeout_ms)
                cfg100 = None
                if 100 in strengths:
                    cfg100 = _wait_configure_at_enhancement(page, 100, timeout_ms=timeout_ms)

                stem = src.stem
                pair_dir = output_dir / stem
                pair_dir.mkdir(parents=True, exist_ok=True)

                strength_paths: dict[str, str] = {}
                strength_urls: dict[int, str] = {
                    0: cfg0.get("url") or original_url,
                    70: cfg70.get("url") or original_url,
                }
                if cfg100:
                    strength_urls[100] = cfg100.get("url") or original_url

                log("  pobieram original / ww70 / ww100...")
                for strength in strengths:
                    src_url = strength_urls.get(strength)
                    if not src_url:
                        continue
                    suffix = "original" if strength == 0 else f"ww{strength}"
                    dest = pair_dir / f"{suffix}.jpg"
                    download_via_request(page.request, src_url, dest, timeout_ms=timeout_ms)
                    strength_paths[str(strength)] = str(dest.relative_to(output_dir))
                    log(f"  zapisano {dest.name}")

                log(f"  gotowe: {pair_dir.name}/")

                manifest = PairManifest(
                    source_file=str(src.resolve()),
                    image_id=image_id,
                    strengths=strength_paths,
                    original_url=original_url,
                    notes=(
                        "original.jpg = WW preview URL (enhancement=0, ten sam crop co ww70); "
                        "original_url w manifescie = surowy imageserver id+token"
                    ),
                )
                manifests.append(manifest)

                meta_path = pair_dir / "manifest.json"
                meta_path.write_text(
                    json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except (ValueError, RuntimeError, TimeoutError, PlaywrightTimeoutError) as exc:
                failed.append({"file": src.name, "reason": str(exc)})
                log(f"  BLAD — pomijam: {exc}")
            except Exception as exc:
                failed.append({"file": src.name, "reason": str(exc)})
                log(f"  BLAD — pomijam: {exc}")
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
                try:
                    context.close()
                except Exception:
                    pass
                if idx < len(eligible):
                    time.sleep(2)

        browser.close()

    if skipped or failed:
        report = {"skipped": skipped, "failed": failed}
        (output_dir / "collect_skipped.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    log(
        f"Podsumowanie: {len(manifests)} par OK, "
        f"{len(skipped)} za malych, {len(failed)} bledow uploadu."
    )
    if not manifests:
        raise RuntimeError(
            f"Nie zebrano zadnej pary. Sprawdz collect_skipped.json w {output_dir} "
            f"i uzyj zdjec min. {WW_MIN_EDGE}x{WW_MIN_EDGE} px."
        )

    try:
        temp_dir.rmdir()
    except OSError:
        pass

    index_path = output_dir / "index.json"
    index_path.write_text(
        json.dumps([m.to_dict() for m in manifests], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifests


def collect_from_image_id(
    image_id: str,
    output_dir: Path,
    *,
    label: str = "manual",
    strengths: tuple[int, ...] = STRENGTHS,
) -> PairManifest:
    """Recznie: masz juz `id` z DevTools (imageserver) — pobiera pary bez uploadu."""
    output_dir = Path(output_dir)
    pair_dir = output_dir / label
    pair_dir.mkdir(parents=True, exist_ok=True)

    strength_paths: dict[str, str] = {}
    for strength in strengths:
        url = build_imageserver_url(image_id, strength)
        suffix = "original" if strength == 0 else f"ww{strength}"
        dest = pair_dir / f"{suffix}.jpg"
        download_url(url, dest)
        strength_paths[str(strength)] = str(dest.relative_to(output_dir))

    manifest = PairManifest(
        source_file="",
        image_id=image_id,
        strengths=strength_paths,
        original_url=build_imageserver_url(image_id, 0),
    )
    (pair_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
