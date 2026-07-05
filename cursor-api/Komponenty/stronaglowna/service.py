"""Strona główna — index.json, ustawienia motywu, upload, backup, deploy."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from Komponenty.dodajobraz import shopify_client as sc

from .registry import HOME_ZONES, SITE_NOTICE_ZONE_ID, HomeField, HomeZone, set_zone_enabled, zone_enabled
from .text_html import (
    body_to_html,
    build_heading_html,
    html_to_body_plain,
    merge_heading_body_html,
    parse_heading,
    split_combined_html,
)

Logger = Callable[[str], None]

INDEX_HEADER = """/*
 * ------------------------------------------------------------
 * IMPORTANT: The contents of this file are auto-generated.
 *
 * This file may be updated by the Shopify admin theme editor
 * or related systems. Please exercise caution as any changes
 * made to this file may be overwritten.
 * ------------------------------------------------------------
 */
"""

SETTINGS_HEADER = INDEX_HEADER

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}
MOBILE_HERO_REL = "assets/MALE_ORG.webp"
_HOMEPAGE_URL = "https://gicleeart.eu/"

SITE_NOTICE_KEYS = {
    "sn_enabled": "site_notice_enabled",
    "sn_version": "site_notice_version",
    "sn_title": "site_notice_title",
    "sn_message": "site_notice_message",
    "sn_button": "site_notice_button",
}

_THUMB_CACHE: dict[str, str | None] = {}


def _log(logger: Logger | None, msg: str) -> None:
    if logger:
        logger(msg)


def _component_dir() -> Path:
    return Path(__file__).resolve().parent


def _data_dir() -> Path:
    return _component_dir() / "data"


def _backups_dir() -> Path:
    return _data_dir() / "backups"


def theme_dev_port_open(*, host: str = "127.0.0.1", port: int = 9292, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def kill_process_listening_on_port(*, host: str = "127.0.0.1", port: int = 9292) -> list[int]:
    """Zabij proces(y) nasłuchujące na porcie (Windows: netstat + taskkill)."""
    killed: list[int] = []
    needle = f"{host}:{port}"
    if sys.platform == "win32":
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in result.stdout.splitlines():
            if needle not in line or "LISTENING" not in line:
                continue
            pid_text = line.split()[-1]
            if not pid_text.isdigit():
                continue
            pid = int(pid_text)
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            killed.append(pid)
        return killed

    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for pid_text in result.stdout.split():
            if pid_text.isdigit():
                pid = int(pid_text)
                subprocess.run(["kill", "-9", str(pid)], capture_output=True)
                killed.append(pid)
    except FileNotFoundError:
        pass
    return killed


def storefront_password_file() -> Path:
    return theme_root() / ".shopify-store-password.local"


def resolve_storefront_password() -> str:
    """Hasło password page sklepu — env, plik lokalny (gitignore) lub integracjagpt secrets."""
    env_pw = os.environ.get("SHOPIFY_FLAG_STORE_PASSWORD", "").strip()
    if env_pw:
        return env_pw

    path = storefront_password_file()
    if path.is_file():
        try:
            line = path.read_text(encoding="utf-8").strip()
            if line:
                return line
        except OSError:
            pass

    return ""


def save_storefront_password(password: str) -> None:
    """Zapis hasła lokalnie (poza repo / lustrem GPT)."""
    path = storefront_password_file()
    pw = password.strip()
    if not pw:
        if path.is_file():
            path.unlink(missing_ok=True)
        return
    path.write_text(pw + "\n", encoding="utf-8")


def theme_dev_cli_args() -> list[str]:
    args = ["theme", "dev", "--environment", "development"]
    pw = resolve_storefront_password()
    if pw:
        args.extend(["--store-password", pw])
    return args


def theme_dev_http_ready(
    *,
    url: str = "http://127.0.0.1:9292/?giclee_skip_splash=1&giclee_skip_notice=1",
    timeout: float = 12.0,
    min_bytes: int = 200,
) -> bool:
    """Port otwarty ≠ serwer odpowiada — weryfikacja HTTP (zombie theme dev)."""
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            body = response.read(min_bytes + 4096)
            if len(body) < min_bytes:
                return False
            text = body.decode("utf-8", errors="replace").lower()
            if "password" in text and (
                "enter_password" in text
                or "storefront-password" in text
                or 'name="password"' in text
                or "password-page" in text
            ):
                return False
            return True
    except (URLError, OSError, TimeoutError, ValueError):
        return False


def resolve_shopify_cli() -> str:
    """Ścieżka do Shopify CLI — na Windows często `shopify.cmd` poza PATH."""
    for name in ("shopify", "shopify.cmd", "shopify.exe"):
        path = shutil.which(name)
        if path:
            return path

    candidates: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "npm" / "shopify.cmd")
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.append(Path(localappdata) / "Programs" / "npm" / "shopify.cmd")
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(Path(program_files) / "nodejs" / "shopify.cmd")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    raise FileNotFoundError(
        "Nie znaleziono Shopify CLI (polecenie «shopify»).\n\n"
        "Zainstaluj: npm install -g @shopify/cli @shopify/theme\n"
        "Albo uruchom ręcznie w terminalu z katalogu motywu:\n"
        "  shopify theme dev --environment development"
    )


def shopify_cli_popen(cli_args: list[str], *, cwd: Path | str) -> subprocess.Popen[str]:
    cli = resolve_shopify_cli()
    env = os.environ.copy()
    pw = resolve_storefront_password()
    if pw:
        env["SHOPIFY_FLAG_STORE_PASSWORD"] = pw
    popen_kw: dict[str, Any] = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
    }
    if sys.platform == "win32" and Path(cli).suffix.lower() in {".cmd", ".bat"}:
        cmdline = subprocess.list2cmdline([cli, *cli_args])
        return subprocess.Popen(cmdline, shell=True, **popen_kw)
    return subprocess.Popen([cli, *cli_args], **popen_kw)


def theme_root() -> Path:
    return Path(__file__).resolve().parents[3]


def index_template_path() -> Path:
    return theme_root() / "templates" / "index.json"


def settings_data_path() -> Path:
    return theme_root() / "config" / "settings_data.json"


def mobile_hero_path() -> Path:
    return theme_root() / "assets" / "MALE_ORG.webp"


def homepage_preview_url() -> str:
    return _HOMEPAGE_URL


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def path_get(root: Any, path: tuple[str, ...]) -> Any:
    cur = root
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def path_set(root: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cur: Any = root
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _block_at(template: dict[str, Any], block_path: tuple[str, ...]) -> dict[str, Any] | None:
    block = path_get(template, block_path)
    return block if isinstance(block, dict) else None


COLOR_CORRECTION_CTA_GROUP: tuple[str, ...] = (
    "sections",
    "section_bj9cY3",
    "blocks",
    "group_FCVUiD",
    "blocks",
    "group_PKPWxV",
)

COLOR_CORRECTION_CTA_PARENT: tuple[str, ...] = COLOR_CORRECTION_CTA_GROUP[:-1]

_COLOR_CORRECTION_CTA_GROUP_CANON: dict[str, Any] = {
    "type": "group",
    "name": "t:names.buttons",
    "settings": {
        "content_direction": "row",
        "vertical_on_mobile": False,
        "horizontal_alignment": "center",
        "vertical_alignment": "center",
        "align_baseline": False,
        "horizontal_alignment_flex_direction_column": "flex-start",
        "vertical_alignment_flex_direction_column": "center",
        "gap": 12,
        "width": "fill",
        "custom_width": 100,
        "width_mobile": "fill",
        "custom_width_mobile": 100,
        "height": "fit",
        "custom_height": 100,
        "inherit_color_scheme": True,
        "color_scheme": "",
        "background_media": "none",
        "video_position": "cover",
        "background_image_position": "cover",
        "border": "none",
        "border_width": 1,
        "border_opacity": 100,
        "border_radius": 0,
        "toggle_overlay": False,
        "overlay_color": "#00000026",
        "overlay_style": "solid",
        "gradient_direction": "to top",
        "link": "",
        "open_in_new_tab": False,
        "placeholder": "",
        "padding-block-start": 0,
        "padding-block-end": 0,
        "padding-inline-start": 0,
        "padding-inline-end": 0,
    },
    "blocks": {
        "button_UgW9Kt": {
            "type": "button",
            "name": "t:names.button",
            "settings": {
                "label": "Wyświetl wszystko",
                "link": "shopify://collections/all",
                "open_in_new_tab": False,
                "style_class": "button-secondary",
                "width": "fit-content",
                "custom_width": 34,
                "width_mobile": "fit-content",
                "custom_width_mobile": 34,
            },
            "blocks": {},
        },
        "button_7G6q7x": {
            "type": "button",
            "name": "t:names.button",
            "settings": {
                "label": "Kup teraz",
                "link": "shopify://collections/all",
                "open_in_new_tab": False,
                "style_class": "button-secondary",
                "width": "fit-content",
                "custom_width": 34,
                "width_mobile": "fit-content",
                "custom_width_mobile": 34,
            },
            "blocks": {},
        },
    },
    "block_order": ["button_UgW9Kt", "button_7G6q7x"],
}


def _merge_button_block(existing: dict[str, Any] | None, canonical: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(canonical)
    if not isinstance(existing, dict):
        return out
    if existing.get("disabled"):
        out["disabled"] = True
    exist_settings = existing.get("settings")
    if isinstance(exist_settings, dict):
        for key, val in exist_settings.items():
            out["settings"][key] = val
    return out


def repair_color_correction_cta_blocks(template: dict[str, Any]) -> bool:
    """Uzupełnia brakujące pola type/name w grupie CTA sekcji korekcji kolorystycznej."""
    parent = path_get(template, COLOR_CORRECTION_CTA_PARENT)
    if not isinstance(parent, dict):
        return False
    blocks = parent.get("blocks")
    if not isinstance(blocks, dict):
        return False
    existing = blocks.get("group_PKPWxV")
    if not isinstance(existing, dict):
        return False

    changed = False
    child_blocks = existing.get("blocks") if isinstance(existing.get("blocks"), dict) else {}
    buttons_ok = (
        existing.get("type") == "group"
        and isinstance(child_blocks.get("button_UgW9Kt"), dict)
        and child_blocks["button_UgW9Kt"].get("type") == "button"
        and isinstance(child_blocks.get("button_7G6q7x"), dict)
        and child_blocks["button_7G6q7x"].get("type") == "button"
    )
    if not buttons_ok:
        canonical = copy.deepcopy(_COLOR_CORRECTION_CTA_GROUP_CANON)
        canonical["blocks"]["button_UgW9Kt"] = _merge_button_block(
            child_blocks.get("button_UgW9Kt") if isinstance(child_blocks, dict) else None,
            canonical["blocks"]["button_UgW9Kt"],
        )
        canonical["blocks"]["button_7G6q7x"] = _merge_button_block(
            child_blocks.get("button_7G6q7x") if isinstance(child_blocks, dict) else None,
            canonical["blocks"]["button_7G6q7x"],
        )
        if existing.get("disabled"):
            canonical["disabled"] = True
        blocks["group_PKPWxV"] = canonical
        changed = True

    order = parent.get("block_order")
    if not isinstance(order, list):
        parent["block_order"] = ["group_AjTVRg", "group_PKPWxV"]
        changed = True
    elif "group_PKPWxV" not in order:
        order.append("group_PKPWxV")
        changed = True
    return changed


def _color_correction_cta_present(template: dict[str, Any]) -> bool:
    return _block_at(template, COLOR_CORRECTION_CTA_GROUP) is not None


def _skip_optional_color_correction_field(
    zone_id: str, field_id: str, template: dict[str, Any]
) -> bool:
    if zone_id != "color_correction":
        return False
    if field_id not in (
        "cc_cta_visible",
        "cc_btn1_label",
        "cc_btn1_link",
        "cc_btn2_label",
        "cc_btn2_link",
    ):
        return False
    return not _color_correction_cta_present(template)


def _read_blocks_visible(template: dict[str, Any], field: HomeField) -> bool:
    paths = field.block_paths
    if not paths:
        return True
    found = False
    for block_path in paths:
        block = _block_at(template, block_path)
        if block is None:
            continue
        found = True
        if block.get("disabled"):
            return False
    return found


def _write_blocks_visible(template: dict[str, Any], field: HomeField, visible: bool) -> None:
    for block_path in field.block_paths:
        block = _block_at(template, block_path)
        if block is None:
            continue
        if visible:
            block.pop("disabled", None)
        else:
            block["disabled"] = True


def load_index_template(*, logger: Logger | None = None) -> dict[str, Any]:
    path = index_template_path()
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku szablonu: {path}")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_json_header(raw))
    if not isinstance(data, dict):
        raise ValueError("index.json — nieprawidłowy format.")
    _log(logger, f"[strona główna] Wczytano {path.name}.")
    return data


def save_index_template(template: dict[str, Any], *, logger: Logger | None = None) -> None:
    repair_color_correction_cta_blocks(template)
    path = index_template_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
    path.write_text(INDEX_HEADER + body, encoding="utf-8")
    _log(logger, f"[strona główna] Zapisano {path.name}.")


def load_theme_settings(*, logger: Logger | None = None) -> dict[str, Any]:
    path = settings_data_path()
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku ustawień: {path}")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(_strip_json_header(raw))
    if not isinstance(data, dict):
        raise ValueError("settings_data.json — nieprawidłowy format.")
    _log(logger, f"[strona główna] Wczytano {path.name}.")
    return data


def save_theme_settings(data: dict[str, Any], *, logger: Logger | None = None) -> None:
    path = settings_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(SETTINGS_HEADER + body, encoding="utf-8")
    _log(logger, f"[strona główna] Zapisano {path.name}.")


def _settings_current(data: dict[str, Any]) -> dict[str, Any]:
    current = data.get("current")
    if not isinstance(current, dict):
        current = {}
        data["current"] = current
    return current


def backup_file(path: Path, *, label: str, logger: Logger | None = None) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Brak pliku do kopii: {path}")
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_dir = _backups_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    if path.name == "index.json":
        stamped = backup_dir / f"index-{ts}.json"
    elif path.name == "settings_data.json":
        stamped = backup_dir / f"settings-{ts}.json"
    else:
        stamped = backup_dir / f"{path.stem}-{ts}{path.suffix}"
    shutil.copy2(path, stamped)
    _log(logger, f"[strona główna] Kopia {label}: {stamped.name}")
    return stamped


def backup_before_save(*, logger: Logger | None = None) -> list[Path]:
    saved: list[Path] = []
    index_path = index_template_path()
    if index_path.is_file():
        saved.append(backup_file(index_path, label="index.json", logger=logger))
    settings_path = settings_data_path()
    if settings_path.is_file():
        saved.append(backup_file(settings_path, label="settings_data.json", logger=logger))
    return saved


def shopify_ref_label(ref: str | None) -> str:
    text = (ref or "").strip()
    if not text:
        return "(brak)"
    if text.startswith("shopify://shop_images/"):
        return text.rsplit("/", 1)[-1]
    if text.startswith("shopify://files/videos/"):
        return text.rsplit("/", 1)[-1]
    if text.startswith("gid://shopify/Video/"):
        return f"film ({text.rsplit('/', 1)[-1][:12]}…)"
    return text


def cdn_url_to_shopify_ref(cdn_url: str, *, fallback_name: str) -> str:
    parsed = urlparse(cdn_url or "")
    name = unquote(parsed.path.rsplit("/", 1)[-1] if parsed.path else "") or fallback_name
    if Path(name).suffix.lower() in VIDEO_SUFFIXES:
        return f"shopify://files/videos/{name}"
    return f"shopify://shop_images/{name}"


def resolve_shopify_image_url(ref: str, *, logger: Logger | None = None) -> str | None:
    text = (ref or "").strip()
    if not text:
        return None
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text in _THUMB_CACHE:
        return _THUMB_CACHE[text]
    if text.startswith("shopify://files/videos/") or text.startswith("gid://shopify/Video/"):
        return _resolve_shopify_video_preview_url(text, logger=logger)
    if not text.startswith("shopify://shop_images/"):
        return None
    filename = text.rsplit("/", 1)[-1]
    shop, token = sc.load_session()
    query = """
    query FilesByName($q: String!) {
      files(first: 5, query: $q) {
        nodes {
          ... on MediaImage { image { url } }
          ... on GenericFile { url }
        }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"q": f"filename:{filename}"})
        nodes = ((data or {}).get("files") or {}).get("nodes") or []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            image = node.get("image")
            if isinstance(image, dict) and image.get("url"):
                url = str(image["url"])
                _THUMB_CACHE[text] = url
                return url
            if node.get("url"):
                url = str(node["url"])
                _THUMB_CACHE[text] = url
                return url
    except Exception as exc:
        _log(logger, f"[strona główna] CDN lookup {filename}: {exc}")
    _THUMB_CACHE[text] = None
    return None


def _resolve_shopify_video_preview_url(ref: str, *, logger: Logger | None = None) -> str | None:
    if ref in _THUMB_CACHE:
        return _THUMB_CACHE[ref]
    shop, token = sc.load_session()
    if ref.startswith("gid://"):
        query = """
        query VideoPreview($id: ID!) {
          node(id: $id) {
            ... on Video { preview { image { url } } }
          }
        }
        """
        try:
            data = sc.graphql(shop, token, query, {"id": ref})
            node = (data or {}).get("node") or {}
            preview = node.get("preview") or {}
            image = preview.get("image") if isinstance(preview, dict) else None
            if isinstance(image, dict) and image.get("url"):
                url = str(image["url"])
                _THUMB_CACHE[ref] = url
                return url
        except Exception as exc:
            _log(logger, f"[strona główna] video preview gid: {exc}")
        _THUMB_CACHE[ref] = None
        return None
    filename = ref.rsplit("/", 1)[-1]
    shop, token = sc.load_session()
    query = """
    query FilesByName($q: String!) {
      files(first: 5, query: $q) {
        nodes {
          ... on Video { preview { image { url } } }
          ... on GenericFile { url }
        }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"q": f"filename:{filename}"})
        nodes = ((data or {}).get("files") or {}).get("nodes") or []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            preview = node.get("preview") or {}
            image = preview.get("image") if isinstance(preview, dict) else None
            if isinstance(image, dict) and image.get("url"):
                url = str(image["url"])
                _THUMB_CACHE[ref] = url
                return url
            if node.get("url"):
                url = str(node["url"])
                _THUMB_CACHE[ref] = url
                return url
    except Exception as exc:
        _log(logger, f"[strona główna] video preview {filename}: {exc}")
    _THUMB_CACHE[ref] = None
    return None


def resolve_shopify_file_download_url(ref: str, *, logger: Logger | None = None) -> str | None:
    """URL do pobrania pliku z Shopify Files (obraz lub wideo)."""
    text = (ref or "").strip()
    if not text.startswith("shopify://") and not text.startswith("gid://"):
        return None
    if text.startswith("shopify://shop_images/"):
        return resolve_shopify_image_url(text, logger=logger)
    shop, token = sc.load_session()
    if text.startswith("gid://shopify/Video/"):
        query = """
        query VideoDownload($id: ID!) {
          node(id: $id) {
            ... on Video {
              originalSource { url }
              sources { url mimeType }
            }
          }
        }
        """
        try:
            data = sc.graphql(shop, token, query, {"id": text})
            node = (data or {}).get("node") or {}
            original = node.get("originalSource") or {}
            if isinstance(original, dict) and original.get("url"):
                return str(original["url"])
            sources = node.get("sources") or []
            if isinstance(sources, list):
                for src in reversed(sources):
                    if isinstance(src, dict) and src.get("url"):
                        return str(src["url"])
        except Exception as exc:
            _log(logger, f"[strona główna] download video gid: {exc}")
        return None
    if not text.startswith("shopify://files/videos/"):
        return None
    filename = text.rsplit("/", 1)[-1]
    shop, token = sc.load_session()
    query = """
    query FilesByName($q: String!) {
      files(first: 5, query: $q) {
        nodes {
          ... on Video {
            originalSource { url }
            sources { url mimeType }
          }
          ... on GenericFile { url }
        }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"q": f"filename:{filename}"})
        nodes = ((data or {}).get("files") or {}).get("nodes") or []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            original = node.get("originalSource") or {}
            if isinstance(original, dict) and original.get("url"):
                return str(original["url"])
            sources = node.get("sources") or []
            if isinstance(sources, list):
                for src in reversed(sources):
                    if isinstance(src, dict) and src.get("url"):
                        return str(src["url"])
            if node.get("url"):
                return str(node["url"])
    except Exception as exc:
        _log(logger, f"[strona główna] download URL {filename}: {exc}")
    return None


def fetch_shopify_file_bytes(ref: str, *, logger: Logger | None = None) -> bytes | None:
    url = resolve_shopify_file_download_url(ref, logger=logger)
    if not url:
        return None
    try:
        with urlopen(url, timeout=120) as resp:
            return resp.read()
    except (URLError, OSError, TimeoutError) as exc:
        _log(logger, f"[strona główna] pobieranie {ref}: {exc}")
        return None


def resolve_ffmpeg_exe() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError as exc:
        raise RuntimeError(
            "Brak ffmpeg. Zainstaluj ffmpeg w PATH albo: pip install imageio-ffmpeg"
        ) from exc


def build_boomerang_loop_video(src: Path, dst: Path) -> Path:
    """Łączy oryginał + odwróconą kopię w jeden plik do płynnej pętli HTML5."""
    src = Path(src)
    dst = Path(dst)
    if not src.is_file():
        raise FileNotFoundError(f"Brak pliku wideo: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-filter_complex",
        "[0:v]reverse[r];[0:v][r]concat=n=2:v=1:a=0[outv]",
        "-map",
        "[outv]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"ffmpeg boomerang loop nie powiodło się: {detail or proc.returncode}")
    if not dst.is_file():
        raise RuntimeError("ffmpeg nie utworzył pliku pętli.")
    return dst


def _expected_boomerang_loop_name(forward_ref: str) -> str:
    stem = re.sub(r"[^\w.\-]+", "_", forward_ref.rsplit("/", 1)[-1]).rsplit(".", 1)[0] or "hero"
    return f"{stem}_boomerang.mp4"


def _boomerang_loop_is_current(forward_ref: str, loop_ref: str) -> bool:
    """Czy istniejący plik pętli pasuje do filmu bazowego (Shopify może dodać UUID do nazwy)."""
    loop_ref = str(loop_ref or "").strip()
    if not loop_ref:
        return False
    actual = loop_ref.rsplit("/", 1)[-1]
    expected = _expected_boomerang_loop_name(forward_ref)
    if actual == expected:
        return True
    stem = expected.replace("_boomerang.mp4", "")
    return actual.startswith(f"{stem}_boomerang") and actual.endswith(".mp4")


def sync_hero_boomerang_video(
    zone_values: dict[str, Any],
    *,
    logger: Logger | None = None,
) -> None:
    """Generuje jeden plik MP4 (do przodu + w tył) do płynnej pętli HTML5."""
    boomerang = bool(zone_values.get("hero_video_boomerang"))
    forward = str(zone_values.get("hero_desktop_video") or "").strip()
    loop_ref = str(zone_values.get("hero_desktop_video_reversed") or "").strip()

    if not boomerang:
        zone_values["hero_desktop_video_reversed"] = ""
        return

    if not forward:
        zone_values["hero_desktop_video_reversed"] = ""
        return

    expected_name = _expected_boomerang_loop_name(forward)
    if _boomerang_loop_is_current(forward, loop_ref):
        return

    _log(logger, "[strona główna] Generuję pętlę hero wideo (tam i z powrotem)…")
    raw = fetch_shopify_file_bytes(forward, logger=logger)
    if not raw:
        raise RuntimeError(f"Nie udało się pobrać filmu hero: {forward}")

    tmp_dir = _data_dir() / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    stem = expected_name.replace("_boomerang.mp4", "")
    src = tmp_dir / f"{stem}_src.mp4"
    dst = tmp_dir / expected_name
    src.write_bytes(raw)
    build_boomerang_loop_video(src, dst)
    loop_ref = upload_shopify_video(dst, logger=logger)
    zone_values["hero_desktop_video_reversed"] = loop_ref
    _log(logger, f"[strona główna] Pętla boomerang → {loop_ref}")


def resolve_local_shopify_image_path(ref: str) -> Path | None:
    """Lokalny plik motywu dla shopify://shop_images/… (bez sieci)."""
    text = (ref or "").strip()
    if not text.startswith("shopify://shop_images/"):
        return None
    name = text.rsplit("/", 1)[-1]
    if not name:
        return None
    root = theme_root()
    for candidate in (
        root / "assets" / name,
        root / "assets" / "files" / name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _studio_inline_context() -> bool:
    return os.environ.get("GICLEE_STUDIO_INLINE") == "1"


def fetch_thumbnail_bytes(*, shopify_ref: str = "", local_path: Path | None = None) -> bytes | None:
    if local_path and local_path.is_file():
        return local_path.read_bytes()
    ref = (shopify_ref or "").strip()
    if ref:
        local = resolve_local_shopify_image_path(ref)
        if local and local.is_file():
            return local.read_bytes()
    if _studio_inline_context():
        return None
    url = resolve_shopify_image_url(shopify_ref)
    if not url:
        return None
    try:
        with urlopen(url, timeout=30) as resp:
            return resp.read()
    except (URLError, OSError, TimeoutError):
        return None


DEFAULT_SECTION_OVERLAY_PCT = 100
OVERLAY_PCT_MIN = 0
OVERLAY_PCT_MAX = 100


def normalize_overlay_pct(raw: Any) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = 0
    return max(OVERLAY_PCT_MIN, min(OVERLAY_PCT_MAX, value))


def _section_bg_overlay_path(section_key: str) -> tuple[str, ...]:
    return ("sections", section_key, "settings", "background_overlay_pct")


def _parse_section_background(value: Any) -> dict[str, Any]:
    overlay_pct = 0
    if isinstance(value, dict):
        media = str(value.get("media") or "none").strip().lower()
        ref = str(value.get("ref") or "").strip()
        if media not in ("image", "video"):
            media = "video" if ref.startswith(("shopify://files/videos/", "gid://shopify/Video/")) else (
                "image" if ref.startswith("shopify://") else "none"
            )
        overlay_pct = normalize_overlay_pct(value.get("overlay_pct"))
        if media == "none" or not ref:
            return {"media": "none", "ref": "", "overlay_pct": 0}
        return {"media": media, "ref": ref, "overlay_pct": overlay_pct}
    text = str(value or "").strip()
    if text.startswith("shopify://"):
        if "/videos/" in text or text.startswith("gid://shopify/Video/"):
            return {"media": "video", "ref": text, "overlay_pct": 0}
        return {"media": "image", "ref": text, "overlay_pct": 0}
    return {"media": "none", "ref": "", "overlay_pct": 0}


def _read_section_background(template: dict[str, Any], field: HomeField) -> dict[str, Any]:
    section_key = field.path[1]  # type: ignore[index]
    settings_path = ("sections", section_key, "settings")
    overlay_raw = path_get(template, _section_bg_overlay_path(section_key))
    overlay_pct = normalize_overlay_pct(overlay_raw) if overlay_raw is not None else 0
    media = str(path_get(template, (*settings_path, "background_media")) or "none")
    if media == "video":
        ref = normalize_shopify_video_ref(str(path_get(template, (*settings_path, "video")) or ""))
        if not ref:
            return {"media": "none", "ref": "", "overlay_pct": 0}
        return {"media": "video", "ref": ref, "overlay_pct": overlay_pct}
    if media == "image":
        ref = str(path_get(template, field.path) or "")
        if not ref:
            return {"media": "none", "ref": "", "overlay_pct": 0}
        return {"media": "image", "ref": ref, "overlay_pct": overlay_pct}
    return {"media": "none", "ref": "", "overlay_pct": 0}


def _write_section_background(template: dict[str, Any], field: HomeField, value: Any) -> None:
    section_key = field.path[1]  # type: ignore[index]
    parsed = _parse_section_background(value)
    media = parsed["media"]
    ref = str(parsed.get("ref") or "")
    overlay_pct = normalize_overlay_pct(parsed.get("overlay_pct"))
    settings_path = ("sections", section_key, "settings")
    media_path = (*settings_path, "background_media")
    img_path = (*settings_path, "background_image")
    vid_path = (*settings_path, "video")
    overlay_path = _section_bg_overlay_path(section_key)
    if media == "video" and ref:
        path_set(template, media_path, "video")
        path_set(template, vid_path, normalize_shopify_video_ref(ref))
        path_set(template, img_path, "")
        path_set(template, overlay_path, overlay_pct)
    elif media == "image" and ref.startswith("shopify://"):
        path_set(template, media_path, "image")
        path_set(template, img_path, ref)
        path_set(template, vid_path, "")
        path_set(template, overlay_path, overlay_pct)
    else:
        path_set(template, media_path, "none")
        path_set(template, img_path, "")
        path_set(template, vid_path, "")
        path_set(template, overlay_path, 0)


def read_field(template: dict[str, Any], field: HomeField, *, settings: dict[str, Any] | None = None) -> Any:
    if field.kind == "theme_asset":
        path = mobile_hero_path()
        return path.name if path.is_file() else ""
    if field.kind == "blocks_visible":
        return _read_blocks_visible(template, field)
    if field.kind == "section_background" and field.path:
        return _read_section_background(template, field)
    if settings is not None and field.field_id in SITE_NOTICE_KEYS:
        key = SITE_NOTICE_KEYS[field.field_id]
        val = _settings_current(settings).get(key)
        if field.kind == "bool":
            return bool(val)
        return val if val is not None else ""
    if not field.path:
        return None
    return path_get(template, field.path)


def _heading_tag_key(field_id: str) -> str:
    return f"_{field_id}_tag"


def _load_text_fields(template: dict[str, Any], zone: HomeZone) -> dict[str, Any]:
    out: dict[str, Any] = {}
    by_path: dict[tuple[str, ...], list[HomeField]] = {}
    for fld in zone.fields:
        if fld.kind in ("heading", "body") and fld.path:
            by_path.setdefault(fld.path, []).append(fld)

    handled_paths: set[tuple[str, ...]] = set()
    for fld in zone.fields:
        if fld.kind not in ("heading", "body"):
            continue
        if not fld.path:
            continue
        if fld.path in handled_paths:
            continue
        raw = str(path_get(template, fld.path) or "")
        fields_at_path = by_path.get(fld.path, [])
        if len(fields_at_path) > 1:
            tag, heading, body = split_combined_html(raw)
            handled_paths.add(fld.path)
            for f in fields_at_path:
                if f.kind == "heading":
                    out[f.field_id] = heading
                    out[_heading_tag_key(f.field_id)] = tag
                else:
                    out[f.field_id] = body
        elif fld.kind == "heading":
            tag, heading = parse_heading(raw)
            out[fld.field_id] = heading
            out[_heading_tag_key(fld.field_id)] = tag
        else:
            out[fld.field_id] = html_to_body_plain(raw)
    return out


def _apply_text_fields(template: dict[str, Any], zone: HomeZone, values: dict[str, Any]) -> None:
    by_path: dict[tuple[str, ...], list[HomeField]] = {}
    for fld in zone.fields:
        if fld.kind in ("heading", "body") and fld.path:
            by_path.setdefault(fld.path, []).append(fld)

    for path, fields_at_path in by_path.items():
        heading_fields = [f for f in fields_at_path if f.kind == "heading"]
        body_fields = [f for f in fields_at_path if f.kind == "body"]
        if heading_fields and body_fields:
            hf = heading_fields[0]
            bf = body_fields[0]
            tag = str(values.get(_heading_tag_key(hf.field_id), "h2") or "h2")
            merged = merge_heading_body_html(
                str(values.get(hf.field_id, "") or ""),
                str(values.get(bf.field_id, "") or ""),
                tag=tag,
            )
            path_set(template, path, merged)
        elif heading_fields:
            hf = heading_fields[0]
            tag = str(values.get(_heading_tag_key(hf.field_id), "h2") or "h2")
            path_set(template, path, build_heading_html(str(values.get(hf.field_id, "") or ""), tag=tag))
        elif body_fields:
            bf = body_fields[0]
            path_set(template, path, body_to_html(str(values.get(bf.field_id, "") or "")))


def write_field(template: dict[str, Any], field: HomeField, value: Any) -> None:
    if field.kind in ("heading", "body", "theme_asset"):
        return
    if field.kind == "blocks_visible":
        _write_blocks_visible(template, field, bool(value))
        return
    if not field.path:
        return
    if field.kind == "bool":
        path_set(template, field.path, bool(value))
    elif field.kind == "int":
        try:
            path_set(template, field.path, int(value))
        except (TypeError, ValueError):
            path_set(template, field.path, 0)
    elif field.kind == "media_type":
        raw = str(value or "image").strip().lower()
        if raw in ("video", "collage"):
            path_set(template, field.path, raw)
        else:
            path_set(template, field.path, "image")
    elif field.kind == "video_collage":
        from .video_collage import parse_collage, serialize_collage

        path_set(template, field.path, serialize_collage(parse_collage(value)))
    elif field.kind == "shopify_video":
        path_set(template, field.path, normalize_shopify_video_ref(str(value or "")))
    elif field.kind == "section_background" and field.path:
        _write_section_background(template, field, value)
    else:
        path_set(template, field.path, value)


def load_zone_values(
    template: dict[str, Any],
    zone: HomeZone,
    *,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"_enabled": zone_enabled(template, zone)}
    text_values = _load_text_fields(template, zone)
    out.update(text_values)

    for fld in zone.fields:
        if fld.kind in ("heading", "body"):
            continue
        val = read_field(template, fld, settings=settings)
        if fld.kind == "theme_asset":
            p = mobile_hero_path()
            out[fld.field_id] = p.name if p.is_file() else ""
        elif fld.kind == "bool" or fld.kind == "blocks_visible":
            out[fld.field_id] = bool(val)
        elif fld.kind == "media_type":
            raw = str(val or "image").strip().lower()
            out[fld.field_id] = raw if raw in ("video", "collage") else "image"
        elif fld.kind == "video_collage":
            from .video_collage import parse_collage

            out[fld.field_id] = parse_collage(val)
        elif fld.kind == "section_background":
            out[fld.field_id] = _parse_section_background(val)
        elif fld.kind == "int":
            try:
                out[fld.field_id] = int(val or 0)
            except (TypeError, ValueError):
                out[fld.field_id] = 0
        else:
            out[fld.field_id] = val if val is not None else ""
    return out


def apply_zone_values(
    template: dict[str, Any],
    zone: HomeZone,
    values: dict[str, Any],
    *,
    settings: dict[str, Any] | None = None,
) -> None:
    if zone.settings_only:
        if settings is None:
            return
        current = _settings_current(settings)
        for fld in zone.fields:
            if fld.field_id not in SITE_NOTICE_KEYS:
                continue
            key = SITE_NOTICE_KEYS[fld.field_id]
            raw = values.get(fld.field_id)
            if fld.kind == "bool":
                current[key] = bool(raw)
            else:
                current[key] = str(raw or "")
        return

    set_zone_enabled(template, zone, bool(values.get("_enabled", True)))
    _apply_text_fields(template, zone, values)
    if zone.zone_id == "hero":
        media = str(values.get("hero_media_type") or "image").strip().lower()
        if media != "video":
            values["hero_video_boomerang"] = False
            values["hero_desktop_video_reversed"] = ""
        if media != "collage" and "hero_video_collage" in values:
            from .video_collage import empty_collage

            values["hero_video_collage"] = empty_collage()
    for fld in zone.fields:
        if fld.field_id not in values:
            continue
        if fld.kind in ("heading", "body", "theme_asset"):
            continue
        write_field(template, fld, values[fld.field_id])


def upload_shopify_image(local_path: Path, *, logger: Logger | None = None) -> str:
    local_path = Path(local_path)
    if local_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"Niedozwolone rozszerzenie: {local_path.suffix}")
    url = sc.upload_file_to_shopify_files(local_path, alt=local_path.stem)
    ref = cdn_url_to_shopify_ref(url, fallback_name=local_path.name)
    _THUMB_CACHE.pop(ref, None)
    _log(logger, f"[strona główna] Upload → {ref}")
    return ref


def normalize_shopify_video_ref(ref: str, *, logger: Logger | None = None) -> str:
    """Theme JSON wymaga shopify://files/videos/… — nie gid://shopify/Video/…"""
    text = (ref or "").strip()
    if not text.startswith("gid://shopify/Video/"):
        return text
    try:
        normalized = sc.video_gid_to_shopify_ref(text)
        _log(logger, f"[strona główna] Wideo GID → {normalized}")
        return normalized
    except Exception as exc:
        _log(logger, f"[strona główna] Konwersja GID wideo: {exc}")
        return text


def upload_shopify_video(local_path: Path, *, logger: Logger | None = None) -> str:
    local_path = Path(local_path)
    if local_path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"Niedozwolone rozszerzenie wideo: {local_path.suffix}")
    ref = sc.upload_video_to_shopify_files(local_path, alt=local_path.stem)
    _THUMB_CACHE.pop(ref, None)
    _log(logger, f"[strona główna] Upload wideo → {ref}")
    return ref


def list_shopify_videos(
    *,
    search: str = "",
    limit: int = 120,
    logger: Logger | None = None,
) -> list[dict[str, str]]:
    """Lista filmów z Shopify Files (do pickera w GUI)."""
    shop, token = sc.load_session()
    q = "media_type:VIDEO"
    term = (search or "").strip()
    if term:
        safe = term.replace('"', "").replace(":", " ")
        q = f'media_type:VIDEO filename:*{safe}*'

    query = """
    query ListShopifyVideos($first: Int!, $after: String, $query: String) {
      files(first: $first, after: $after, query: $query, sortKey: UPDATED_AT, reverse: true) {
        nodes {
          __typename
          ... on Video {
            id
            filename
            alt
            createdAt
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    cursor: str | None = None
    page_size = min(50, max(1, limit))

    while len(out) < limit:
        try:
            data = sc.graphql(
                shop,
                token,
                query,
                {"first": page_size, "after": cursor, "query": q},
            )
        except Exception as exc:
            _log(logger, f"[strona główna] list_shopify_videos: {exc}")
            break

        block = (data or {}).get("files") or {}
        nodes = block.get("nodes") or []
        for node in nodes:
            if not isinstance(node, dict) or node.get("__typename") != "Video":
                continue
            filename = str(node.get("filename") or "").strip()
            if not filename or filename in seen:
                continue
            seen.add(filename)
            ref = f"shopify://files/videos/{filename}"
            alt = str(node.get("alt") or "").strip()
            out.append(
                {
                    "ref": ref,
                    "gid": str(node.get("id") or "").strip(),
                    "filename": filename,
                    "alt": alt,
                    "label": _video_list_label(filename, alt),
                    "created_at": str(node.get("createdAt") or ""),
                }
            )
            if len(out) >= limit:
                break

        page_info = block.get("pageInfo") or {}
        if not page_info.get("hasNextPage") or len(out) >= limit:
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break

    return out


def _video_list_label(filename: str, alt: str = "") -> str:
    name = (filename or "").strip()
    alt = (alt or "").strip()
    if alt and alt not in {name, Path(name).stem}:
        return f"{alt} ({name})"
    return name or "(brak)"


def _sanitize_video_filename(name: str, *, required_ext: str) -> str:
    text = (name or "").strip().replace("\\", "/").split("/")[-1]
    ext = required_ext if required_ext.startswith(".") else f".{required_ext}"
    if not text.lower().endswith(ext.lower()):
        stem = Path(text).stem if Path(text).suffix else text
        text = f"{stem}{ext}"
    text = re.sub(r'[<>:"|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", "_", text).strip("._")
    if not text.lower().endswith(ext.lower()):
        text = f"{text}{ext}"
    return text


def _graphql_user_errors(block: dict[str, Any], label: str) -> None:
    errs = block.get("userErrors") or []
    if not errs:
        return
    msgs = "; ".join(str(item.get("message") or item) for item in errs if item)
    raise ValueError(f"{label}: {msgs}" if msgs else label)


def resolve_shopify_video_gid(ref: str, *, logger: Logger | None = None) -> str | None:
    text = (ref or "").strip()
    if text.startswith("gid://shopify/Video/"):
        return text
    if not text.startswith("shopify://files/videos/"):
        return None
    filename = text.rsplit("/", 1)[-1]
    shop, token = sc.load_session()
    query = """
    query VideoGidByName($q: String!) {
      files(first: 1, query: $q) {
        nodes {
          ... on Video { id filename }
        }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"q": f"filename:{filename}"})
        nodes = ((data or {}).get("files") or {}).get("nodes") or []
        for node in nodes:
            if isinstance(node, dict) and node.get("id"):
                return str(node["id"])
    except Exception as exc:
        _log(logger, f"[strona główna] resolve_shopify_video_gid {filename}: {exc}")
    return None


def rename_shopify_video(
    ref: str,
    new_name: str,
    *,
    gid: str = "",
    logger: Logger | None = None,
) -> dict[str, str]:
    """Zmienia nazwę pliku wideo w Shopify Files. Gdy API nie pozwala — aktualizuje alt (opis)."""
    old_ref = (ref or "").strip()
    file_gid = (gid or "").strip() or resolve_shopify_video_gid(old_ref, logger=logger)
    if not file_gid:
        raise ValueError("Nie znaleziono pliku wideo w Shopify Files.")

    old_filename = old_ref.rsplit("/", 1)[-1] if old_ref.startswith("shopify://files/videos/") else ""
    ext = Path(old_filename).suffix.lower()
    if ext not in VIDEO_SUFFIXES:
        ext = ".mp4"
    cleaned = _sanitize_video_filename(new_name, required_ext=ext)
    if not cleaned:
        raise ValueError("Podaj prawidłową nazwę pliku.")

    shop, token = sc.load_session()
    mutation = """
    mutation fileUpdate($files: [FileUpdateInput!]!) {
      fileUpdate(files: $files) {
        files {
          ... on Video { id filename alt }
        }
        userErrors { field message code }
      }
    }
    """

    if cleaned != old_filename:
        try:
            data = sc.graphql(shop, token, mutation, {"files": [{"id": file_gid, "filename": cleaned}]})
            res = (data or {}).get("fileUpdate") or {}
            _graphql_user_errors(res, "Zmiana nazwy pliku")
            files = res.get("files") or []
            node = files[0] if files else {}
            actual = str((node or {}).get("filename") or cleaned).strip() or cleaned
            new_ref = f"shopify://files/videos/{actual}"
            _THUMB_CACHE.pop(old_ref, None)
            _THUMB_CACHE.pop(new_ref, None)
            _log(logger, f"[strona główna] Rename wideo {old_filename} → {actual}")
            return {
                "ref": new_ref,
                "filename": actual,
                "label": _video_list_label(actual, str((node or {}).get("alt") or "")),
                "note": "",
            }
        except ValueError as exc:
            _log(logger, f"[strona główna] Rename filename odrzucone: {exc}")

    alt = Path(cleaned).stem
    data = sc.graphql(shop, token, mutation, {"files": [{"id": file_gid, "alt": alt}]})
    res = (data or {}).get("fileUpdate") or {}
    _graphql_user_errors(res, "Zmiana opisu pliku")
    files = res.get("files") or []
    node = files[0] if files else {}
    filename = str((node or {}).get("filename") or old_filename).strip() or old_filename
    actual_alt = str((node or {}).get("alt") or alt).strip() or alt
    same_ref = f"shopify://files/videos/{filename}"
    _THUMB_CACHE.pop(old_ref, None)
    _THUMB_CACHE.pop(same_ref, None)
    note = (
        "Shopify nie zmienił nazwy pliku wideo — zapisano opis (alt). "
        "Pełna zmiana nazwy wymaga usunięcia i ponownego wgrania."
    )
    if cleaned == old_filename:
        note = "Zaktualizowano opis (alt) pliku."
    _log(logger, f"[strona główna] Alt wideo {filename} → {actual_alt}")
    return {
        "ref": same_ref,
        "filename": filename,
        "label": _video_list_label(filename, actual_alt),
        "note": note,
    }


def delete_shopify_video(
    ref: str,
    *,
    gid: str = "",
    logger: Logger | None = None,
) -> None:
    """Usuwa film z Shopify Files (`fileDelete`)."""
    file_gid = (gid or "").strip() or resolve_shopify_video_gid(ref, logger=logger)
    if not file_gid:
        raise ValueError("Nie znaleziono pliku wideo w Shopify Files.")
    shop, token = sc.load_session()
    mutation = """
    mutation fileDelete($fileIds: [ID!]!) {
      fileDelete(fileIds: $fileIds) {
        deletedFileIds
        userErrors { field message code }
      }
    }
    """
    data = sc.graphql(shop, token, mutation, {"fileIds": [file_gid]})
    res = (data or {}).get("fileDelete") or {}
    _graphql_user_errors(res, "Usuwanie pliku")
    if not (res.get("deletedFileIds") or []):
        raise ValueError("Shopify nie potwierdził usunięcia pliku.")
    _THUMB_CACHE.pop((ref or "").strip(), None)
    _log(logger, f"[strona główna] Usunięto wideo {ref}")


def copy_theme_asset(local_path: Path, *, rel_path: str, logger: Logger | None = None) -> str:
    local_path = Path(local_path)
    if local_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"Niedozwolone rozszerzenie: {local_path.suffix}")
    dest = theme_root() / rel_path.replace("\\", "/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, dest)
    _log(logger, f"[strona główna] Skopiowano do motywu: {rel_path}")
    return str(dest)


def copy_mobile_hero(local_path: Path, *, logger: Logger | None = None) -> str:
    return copy_theme_asset(local_path, rel_path=MOBILE_HERO_REL, logger=logger)


def html_to_plain_preview(html: str, *, max_len: int = 120) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


def zone_summary(
    template: dict[str, Any],
    zone: HomeZone,
    *,
    settings: dict[str, Any] | None = None,
) -> str:
    if zone.zone_id == SITE_NOTICE_ZONE_ID and settings is not None:
        current = _settings_current(settings)
        if not current.get("site_notice_enabled"):
            return "modal wyłączony"
        title = str(current.get("site_notice_title") or "").strip()
        return title or "modal włączony"

    enabled = zone_enabled(template, zone)
    if not enabled:
        return "wyłączona"
    parts: list[str] = []
    for fld in zone.fields:
        if fld.kind in ("shopify_image", "shopify_video", "theme_asset"):
            label = shopify_ref_label(str(read_field(template, fld) or ""))
            if label != "(brak)":
                parts.append(label)
        elif fld.kind == "section_background":
            bg = read_field(template, fld)
            if isinstance(bg, dict):
                ref = str(bg.get("ref") or "")
                if ref:
                    prefix = "film: " if bg.get("media") == "video" else ""
                    parts.append(prefix + shopify_ref_label(ref))
    if parts:
        return ", ".join(parts[:2]) + ("…" if len(parts) > 2 else "")
    for fld in zone.fields:
        if fld.kind == "heading":
            raw = str(read_field(template, fld) or "")
            _, heading = parse_heading(raw)
            if heading:
                return heading[:48] + ("…" if len(heading) > 48 else "")
    return "aktywna"


def list_zones(template: dict[str, Any], *, settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for zone in HOME_ZONES:
        rows.append(
            {
                "zone_id": zone.zone_id,
                "label": zone.label,
                "description": zone.description,
                "enabled": zone_enabled(template, zone) if not zone.settings_only else True,
                "summary": zone_summary(template, zone, settings=settings),
            }
        )
    return rows


def validate_template_paths(template: dict[str, Any], *, logger: Logger | None = None) -> list[str]:
    missing: list[str] = []
    for zone in HOME_ZONES:
        if zone.settings_only:
            continue
        for fld in zone.fields:
            if fld.kind in ("heading", "body", "theme_asset"):
                continue
            if _skip_optional_color_correction_field(zone.zone_id, fld.field_id, template):
                continue
            if fld.kind == "blocks_visible":
                if not _color_correction_cta_present(template) and fld.field_id == "cc_cta_visible":
                    continue
                for block_path in fld.block_paths:
                    if _block_at(template, block_path) is None:
                        missing.append(f"{zone.label} → {fld.label}")
                continue
            if fld.kind == "section_background":
                section = (template.get("sections") or {}).get(zone.section_key)
                if not isinstance(section, dict):
                    missing.append(f"{zone.label} → {fld.label}")
                continue
            if not fld.path:
                continue
            if path_get(template, fld.path) is None:
                missing.append(f"{zone.label} → {fld.label}")
    if missing and logger:
        _log(logger, f"[strona główna] Brak {len(missing)} pól w index.json.")
    return missing


def deploy_theme(
    *,
    environment: str = "development",
    allow_live: bool = False,
    on_line: Callable[[str], None] | None = None,
    logger: Logger | None = None,
) -> int:
    """Uruchamia `shopify theme push --environment <env>` z katalogu motywu."""
    root = theme_root()
    toml = root / "shopify.theme.toml"
    if not toml.is_file():
        raise FileNotFoundError(f"Brak {toml.name} — uruchom deploy z katalogu motywu.")

    cli_args = ["theme", "push", "--environment", environment, "--json"]
    if allow_live:
        cli_args.append("--allow-live")

    _log(logger, f"[strona główna] Deploy: shopify {' '.join(cli_args)} (cwd={root})")
    proc = shopify_cli_popen(cli_args, cwd=root)
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line and on_line:
            on_line(line)
    code = proc.wait()
    _log(logger, f"[strona główna] Deploy exit code: {code}")
    return int(code)
