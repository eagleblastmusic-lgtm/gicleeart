"""Wywolanie oficjalnego @squoosh/cli (ten sam silnik WASM co squoosh.app)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .converter import DEFAULT_METHOD, DEFAULT_QUALITY, _flatten_on_white, _HAS_PIL, fit_image_for_webp

if _HAS_PIL:
    from PIL import Image, ImageOps  # type: ignore


def cursor_api_root() -> Path:
    return Path(__file__).resolve().parents[2]


def squoosh_cli_entry() -> Path:
    return cursor_api_root() / "node_modules" / "@squoosh" / "cli" / "src" / "index.js"


def find_node() -> str | None:
    return shutil.which("node")


def squoosh_cli_available() -> tuple[bool, str]:
    """Czy mozna uzyc @squoosh/cli (node + paczka w cursor-api)."""
    node = find_node()
    if not node:
        return False, "Brak Node.js w PATH."
    cli = squoosh_cli_entry()
    if not cli.is_file():
        return (
            False,
            "Brak @squoosh/cli — w folderze cursor-api uruchom: npm install --force",
        )
    try:
        subprocess.run(
            [
                node,
                "--no-experimental-global-navigator",
                "--no-experimental-fetch",
                str(cli),
                "--help",
            ],
            capture_output=True,
            check=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
            cwd=str(cursor_api_root()),
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        return False, f"Squoosh CLI nie odpowiada: {e}"
    return True, "OK"


def build_webp_config(
    *,
    quality: int,
    method: int,
    lossless: bool,
    preserve_alpha: bool,
) -> str:
    """JSON jak w Squoosh CLI: pojedyncze cudzyslowy w srodku."""
    q = max(1, min(100, int(quality)))
    m = max(0, min(6, int(method)))
    opts: dict[str, int | bool] = {
        "quality": q,
        "method": m,  # „Effort” w squoosh.app
        "lossless": 1 if lossless else 0,
    }
    if preserve_alpha:
        opts["alpha_compression"] = 1
        opts["alpha_filtering"] = 1
        opts["alpha_quality"] = 100
    else:
        opts["alpha_compression"] = 0
    parts: list[str] = []
    for key, val in opts.items():
        if isinstance(val, bool):
            parts.append(f"'{key}':{str(val).lower()}")
        else:
            parts.append(f"'{key}':{val}")
    return "{" + ",".join(parts) + "}"


def _image_has_alpha(path: Path) -> bool:
    if not _HAS_PIL:
        return False
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA"):
            return True
        if im.mode == "P" and "transparency" in im.info:
            return True
    return False


def _prepare_input_for_cli(src: Path, *, preserve_alpha: bool) -> tuple[Path, Path | None]:
    """Przygotowuje wejscie: EXIF, limit rozmiaru WebP, opcjonalnie splaszczenie alfy."""
    if not _HAS_PIL:
        if not preserve_alpha and _image_has_alpha(src):
            raise RuntimeError("Brak Pillow do przygotowania obrazu przed Squoosh CLI.")
        return src, None

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if getattr(im, "is_animated", False):
            im.seek(0)
        work = im.copy()
        work, _resize_note = fit_image_for_webp(work)
        needs_flat = not preserve_alpha and (
            work.mode in ("RGBA", "LA")
            or (work.mode == "P" and "transparency" in work.info)
        )
        oversized = work.size != im.size
        if not needs_flat and not oversized:
            return src, None

        tmp = Path(tempfile.mkdtemp(prefix="squoosh_prep_"))
        prep = tmp / f"{src.stem}.png"
        if needs_flat:
            out = _flatten_on_white(work)
        elif preserve_alpha:
            out = work.convert("RGBA")
        else:
            out = work.convert("RGB")
        out.save(prep, format="PNG")
        return prep, tmp


def convert_squoosh_cli(
    src: Path,
    dest: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    method: int = DEFAULT_METHOD,
    lossless: bool = False,
    preserve_alpha: bool = False,
) -> None:
    node = find_node()
    cli = squoosh_cli_entry()
    if not node or not cli.is_file():
        raise RuntimeError(
            "Squoosh CLI niedostepny. Zainstaluj: cd cursor-api && npm install --force"
        )

    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cli_src, tmp_dir = _prepare_input_for_cli(src, preserve_alpha=preserve_alpha)
    config = build_webp_config(
        quality=quality,
        method=method,
        lossless=lossless,
        preserve_alpha=preserve_alpha,
    )

    cmd = [
        node,
        "--no-experimental-global-navigator",
        "--no-experimental-fetch",
        str(cli),
        "--webp",
        config,
        "-d",
        str(dest.parent),
        str(cli_src.resolve()),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cursor_api_root()),
            timeout=600,
        )
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"Squoosh CLI exit {proc.returncode}")

    produced = dest.parent / f"{cli_src.stem}.webp"
    if not produced.is_file():
        raise RuntimeError(f"Squoosh nie utworzyl pliku: {produced}")
    if produced.resolve() != dest.resolve():
        if dest.is_file():
            dest.unlink()
        produced.replace(dest)
