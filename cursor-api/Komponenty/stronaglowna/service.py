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
    popen_kw: dict[str, Any] = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
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


def _read_blocks_visible(template: dict[str, Any], field: HomeField) -> bool:
    paths = field.block_paths
    if not paths:
        return True
    for block_path in paths:
        block = _block_at(template, block_path)
        if block is None:
            continue
        if block.get("disabled"):
            return False
    return True


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
    sidecar = path.with_name(path.name + ".bak")
    shutil.copy2(path, sidecar)
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
    return text


def cdn_url_to_shopify_ref(cdn_url: str, *, fallback_name: str) -> str:
    parsed = urlparse(cdn_url or "")
    name = unquote(parsed.path.rsplit("/", 1)[-1] if parsed.path else "") or fallback_name
    return f"shopify://shop_images/{name}"


def resolve_shopify_image_url(ref: str, *, logger: Logger | None = None) -> str | None:
    text = (ref or "").strip()
    if not text:
        return None
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text in _THUMB_CACHE:
        return _THUMB_CACHE[text]
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


def fetch_thumbnail_bytes(*, shopify_ref: str = "", local_path: Path | None = None) -> bytes | None:
    if local_path and local_path.is_file():
        return local_path.read_bytes()
    url = resolve_shopify_image_url(shopify_ref)
    if not url:
        return None
    try:
        with urlopen(url, timeout=30) as resp:
            return resp.read()
    except (URLError, OSError, TimeoutError):
        return None


def read_field(template: dict[str, Any], field: HomeField, *, settings: dict[str, Any] | None = None) -> Any:
    if field.kind == "theme_asset":
        path = mobile_hero_path()
        return path.name if path.is_file() else ""
    if field.kind == "blocks_visible":
        return _read_blocks_visible(template, field)
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
        if fld.kind not in ("shopify_image", "theme_asset"):
            continue
        label = shopify_ref_label(str(read_field(template, fld) or ""))
        if label != "(brak)":
            parts.append(label)
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
            if fld.kind == "blocks_visible":
                for block_path in fld.block_paths:
                    if _block_at(template, block_path) is None:
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
