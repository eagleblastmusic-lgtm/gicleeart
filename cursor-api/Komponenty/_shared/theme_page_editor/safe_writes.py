"""Atomic, read-back-validated writes for shared theme page editors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

_INSTALLED = False


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _atomic_json_write(path: Path, data: dict[str, Any], *, header: str = "") -> None:
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, header + body)

    parsed = json.loads(_strip_json_header(path.read_text(encoding="utf-8")))
    if not isinstance(parsed, dict):
        raise ValueError(f"Readback zapisu nie zwrócił obiektu JSON: {path}")


def install_atomic_theme_page_writes() -> None:
    """Install atomic writers before gui_shell binds service functions."""

    global _INSTALLED
    if _INSTALLED:
        return

    from . import service_base, variants

    def save_template_to_path(
        path: Path,
        template: dict[str, Any],
        *,
        logger=None,
    ) -> None:
        rel = str(path).replace("\\", "/")
        header = service_base.INDEX_HEADER if "/templates/" in rel else ""
        _atomic_json_write(path, template, header=header)
        service_base._log(logger, f"Zapisano {path.name}.")

    def save_variant_json(
        path: Path,
        data: dict[str, Any],
        *,
        header: str | None = None,
    ) -> None:
        if header is None:
            rel = str(path).replace("\\", "/")
            header = service_base.INDEX_HEADER if "/templates/" in rel else ""
        _atomic_json_write(path, data, header=header)

    def save_manifest(config, manifest: dict[str, Any]) -> None:
        _atomic_json_write(variants.manifest_path(config), manifest)

    service_base.save_template_to_path = save_template_to_path
    variants.save_template_to_path = save_template_to_path
    variants._save_json_file = save_variant_json
    variants.save_manifest = save_manifest
    _INSTALLED = True


__all__ = ["install_atomic_theme_page_writes"]
