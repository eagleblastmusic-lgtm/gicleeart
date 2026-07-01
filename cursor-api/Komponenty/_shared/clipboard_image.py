"""Kopiowanie obrazu (URL / Pillow) do schowka systemowego."""

from __future__ import annotations

import ctypes
from typing import Any
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

_FETCH_HEADERS = {"User-Agent": "GicleeApp-ClipboardImage/1.0"}


def shopify_sized_image_url(url: str, *, width: int) -> str:
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}width={width}"


def fetch_image_bytes(url: str, *, timeout: float = 30.0) -> bytes:
    req = Request(url, headers=_FETCH_HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _configure_win_clipboard_ctypes() -> tuple[Any, Any]:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    return kernel32, user32


def _copy_pil_via_ctypes(image: Image.Image) -> None:
    output = BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()

    CF_DIB = 8
    GMEM_MOVEABLE = 0x0002
    kernel32, user32 = _configure_win_clipboard_ctypes()

    if not user32.OpenClipboard(None):
        raise OSError("Nie mozna otworzyc schowka.")
    h_global = None
    try:
        user32.EmptyClipboard()
        h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_global:
            raise OSError("Nie mozna przydzielic pamieci na obraz.")
        locked = kernel32.GlobalLock(h_global)
        if not locked:
            raise OSError("Nie mozna zablokowac bufora obrazu.")
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        ctypes.memmove(locked, buf, len(data))
        kernel32.GlobalUnlock(h_global)
        if not user32.SetClipboardData(CF_DIB, h_global):
            raise OSError("Nie mozna zapisac obrazu w schowku.")
        h_global = None
    finally:
        if h_global:
            kernel32.GlobalFree(h_global)
        user32.CloseClipboard()


def _copy_pil_via_powershell(image: Image.Image) -> None:
    fd, tmp_name = tempfile.mkstemp(suffix=".png")
    path = Path(tmp_name)
    try:
        import os

        os.close(fd)
        image.save(path, format="PNG")
        path_ps = str(path.resolve()).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            f"$img = [System.Drawing.Image]::FromFile('{path_ps}'); "
            "[System.Windows.Forms.Clipboard]::SetImage($img); "
            "$img.Dispose()"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True,
            text=True,
            timeout=45,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise OSError(err or "PowerShell nie skopiowal obrazu do schowka.")
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def copy_pil_image_to_clipboard(image: Image.Image) -> None:
    """Windows: schowek jako bitmapa. Wymaga Pillow."""
    if not _HAS_PIL:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")
    if sys.platform != "win32":
        raise OSError("Kopiowanie obrazu do schowka jest dostepne tylko w Windows.")

    try:
        _copy_pil_via_powershell(image)
    except OSError:
        _copy_pil_via_ctypes(image)


def _pil_to_dib_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()
    return data


def copy_text_and_image_url_to_clipboard(
    text: str,
    url: str,
    *,
    max_width: int = 1600,
) -> None:
    """Kopiuje tekst i obraz do schowka (Windows). Uwaga: Gemini przy Ctrl+V bierze tylko obraz."""
    if not (text or "").strip():
        raise ValueError("Brak tekstu do skopiowania.")
    if not url:
        raise ValueError("Brak adresu obrazu.")
    if not _HAS_PIL:
        raise RuntimeError("Brak Pillow — zainstaluj: pip install Pillow")
    if sys.platform != "win32":
        raise OSError("Kopiowanie tekstu i obrazu jest dostepne tylko w Windows.")

    sized = shopify_sized_image_url(url, width=max_width)
    raw = fetch_image_bytes(sized)
    with Image.open(BytesIO(raw)) as im:
        pil = im.copy()
        if pil.mode not in ("RGB", "L"):
            pil = pil.convert("RGB")
        if pil.width > max_width:
            ratio = max_width / pil.width
            pil = pil.resize(
                (max_width, max(1, int(pil.height * ratio))),
                Image.Resampling.LANCZOS,
            )
    dib_data = _pil_to_dib_bytes(pil)

    CF_UNICODETEXT = 13
    CF_DIB = 8
    GMEM_MOVEABLE = 0x0002
    kernel32, user32 = _configure_win_clipboard_ctypes()
    text_bytes = text.encode("utf-16-le") + b"\x00\x00"

    if not user32.OpenClipboard(None):
        raise OSError("Nie mozna otworzyc schowka.")
    h_text = None
    h_img = None
    try:
        user32.EmptyClipboard()

        h_text = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
        if not h_text:
            raise OSError("Nie mozna przydzielic pamieci na tekst.")
        locked = kernel32.GlobalLock(h_text)
        if not locked:
            raise OSError("Nie mozna zablokowac bufora tekstu.")
        buf_text = (ctypes.c_char * len(text_bytes)).from_buffer_copy(text_bytes)
        ctypes.memmove(locked, buf_text, len(text_bytes))
        kernel32.GlobalUnlock(h_text)
        if not user32.SetClipboardData(CF_UNICODETEXT, h_text):
            raise OSError("Nie mozna zapisac tekstu w schowku.")
        h_text = None

        h_img = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib_data))
        if not h_img:
            raise OSError("Nie mozna przydzielic pamieci na obraz.")
        locked = kernel32.GlobalLock(h_img)
        if not locked:
            raise OSError("Nie mozna zablokowac bufora obrazu.")
        buf_img = (ctypes.c_char * len(dib_data)).from_buffer_copy(dib_data)
        ctypes.memmove(locked, buf_img, len(dib_data))
        kernel32.GlobalUnlock(h_img)
        if not user32.SetClipboardData(CF_DIB, h_img):
            raise OSError("Nie mozna zapisac obrazu w schowku.")
        h_img = None
    finally:
        if h_text:
            kernel32.GlobalFree(h_text)
        if h_img:
            kernel32.GlobalFree(h_img)
        user32.CloseClipboard()


def image_url_extension(url: str, *, default: str = ".jpg") -> str:
    tail = url.rsplit("/", 1)[-1].split("?", 1)[0]
    ext = Path(tail).suffix.lower()
    if ext == ".jpeg":
        return ".jpg"
    if ext in {".jpg", ".png", ".webp", ".gif"}:
        return ext
    return default


def save_image_url_to_file(
    url: str,
    dest: Path | str,
    *,
    max_width: int = 1600,
) -> Path:
    """Pobiera obraz z URL i zapisuje na dysku."""
    if not url:
        raise ValueError("Brak adresu obrazu.")
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    sized = shopify_sized_image_url(url, width=max_width)
    dest_path.write_bytes(fetch_image_bytes(sized))
    return dest_path


def copy_image_url_to_clipboard(url: str, *, max_width: int = 1600) -> None:
    """Pobiera obraz z URL i wkleja do schowka jako bitmapę."""
    if not url:
        raise ValueError("Brak adresu obrazu.")
    sized = shopify_sized_image_url(url, width=max_width)
    raw = fetch_image_bytes(sized)
    with Image.open(BytesIO(raw)) as im:
        pil = im.copy()
        if pil.mode not in ("RGB", "L"):
            pil = pil.convert("RGB")
        if pil.width > max_width:
            ratio = max_width / pil.width
            pil = pil.resize(
                (max_width, max(1, int(pil.height * ratio))),
                Image.Resampling.LANCZOS,
            )
    copy_pil_image_to_clipboard(pil)
