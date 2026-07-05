"""Diff, walidacja, historia kopii — edytor stron menu."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from Komponenty.stronaglowna.home_features import DEPLOY_TARGETS
from Komponenty.stronaglowna.service import shopify_ref_label

from .config import PageEditorConfig
from .service_base import (
    backups_dir_for,
    load_zone_values,
    template_path_for_config,
    validate_template_paths,
    zone_enabled,
)
from .types import TemplateZone

__all__ = ["DEPLOY_TARGETS", "ChangeItem", "ChangeSummary", "ValidationIssue", "compute_changes", "list_backups", "restore_backup", "validate_page"]


@dataclass
class ChangeItem:
    category: str
    zone_label: str
    field_label: str
    detail: str = ""


@dataclass
class ChangeSummary:
    items: list[ChangeItem] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in self.items:
            out[item.category] = out.get(item.category, 0) + 1
        return out

    def headline(self) -> str:
        if not self.items:
            return "Brak zmian względem wczytanego stanu."
        parts: list[str] = []
        labels = {
            "image": "grafik",
            "heading": "nagłówków",
            "body": "treści",
            "text": "pól tekstowych",
            "bool": "ustawień",
            "visibility": "widoczności sekcji",
        }
        for key, n in self.counts.items():
            label = labels.get(key, key)
            parts.append(f"{n} {label}")
        return "Zmieniono: " + ", ".join(parts) + "."


@dataclass
class ValidationIssue:
    level: str
    zone_label: str
    message: str


def _field_category(kind: str) -> str:
    if kind in ("shopify_image", "shopify_video", "theme_asset", "section_background"):
        return "image"
    if kind == "heading":
        return "heading"
    if kind == "body":
        return "body"
    if kind in ("bool", "blocks_visible"):
        return "bool" if kind == "bool" else "visibility"
    return "text"


def compute_changes(
    config: PageEditorConfig,
    baseline_template: dict[str, Any],
    pending_template: dict[str, Any],
) -> ChangeSummary:
    summary = ChangeSummary()
    for zone in config.zones:
        base_vals = load_zone_values(baseline_template, zone)
        new_vals = load_zone_values(pending_template, zone)
        if bool(base_vals.get("_enabled")) != bool(new_vals.get("_enabled")):
            summary.items.append(
                ChangeItem(
                    "visibility",
                    zone.label,
                    "Widoczność sekcji",
                    "wł." if new_vals.get("_enabled") else "wył.",
                )
            )
        for fld in zone.fields:
            old = base_vals.get(fld.field_id)
            new = new_vals.get(fld.field_id)
            if old == new:
                continue
            cat = _field_category(fld.kind)
            detail = ""
            if cat == "image":
                detail = f"{shopify_ref_label(str(old or ''))} → {shopify_ref_label(str(new or ''))}"
            elif cat in ("heading", "body", "text"):
                detail = f"«{str(old or '')[:40]}…»" if len(str(old or "")) > 40 else str(old or "(puste)")
            summary.items.append(ChangeItem(cat, zone.label, fld.label, detail))
    return summary


def validate_page(
    config: PageEditorConfig,
    template: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = validate_template_paths(template, config.zones)
    for msg in missing:
        issues.append(ValidationIssue("warn", "", f"Brak pola w szablonie: {msg}"))
    for zone in config.zones:
        if zone.settings_only:
            continue
        if not zone_enabled(template, zone):
            continue
        vals = load_zone_values(template, zone)
        for fld in zone.fields:
            if fld.kind not in ("heading", "body", "text", "link"):
                continue
            raw = vals.get(fld.field_id)
            if raw is None or str(raw).strip() == "":
                issues.append(
                    ValidationIssue("info", zone.label, f"Puste pole: {fld.label}")
                )
    return issues


def list_backups(config: PageEditorConfig) -> list[dict[str, str]]:
    backup_dir = backups_dir_for(config)
    if not backup_dir.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(backup_dir.glob("*.json"), reverse=True):
        rows.append({"name": path.name, "path": str(path)})
    return rows


def restore_backup(config: PageEditorConfig, backup_path: Path) -> None:
    dest = template_path_for_config(config)
    if not backup_path.is_file():
        raise FileNotFoundError(str(backup_path))
    shutil.copy2(backup_path, dest)
