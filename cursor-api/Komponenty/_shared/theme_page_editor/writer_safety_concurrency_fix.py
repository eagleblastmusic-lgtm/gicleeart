"""WS-1.3: izolacja okien edytora i blokada źródeł Apply.

WS-1.2 rozdzielił zapis wariantu od motywu i ograniczył Apply do delty
``variant_base -> wariant``. Ten moduł domyka dwa przypadki współbieżności:

- każde okno pamięta własny hash wariantu z chwili wczytania,
- plan Apply zamraża dokładne bajty wariantu i bazy oraz sprawdza je ponownie
  przed i po zapisie plików docelowych.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Any

from . import variants as varmod
from . import writer_safety as ws
from . import writer_safety_delta_fix as delta
from .service_base import load_zone_values, template_path_for_config


_WINDOW_HASH_ATTR = "_giclee_writer_window_sha256"
_MISSING = object()
_core_apply = ws.apply_bounded_plan


class _WindowLoadedVariant(dict[str, Any]):
    """Słownik wariantu z hashem przypisanym do konkretnego wczytania."""


def _variant_path(config: Any, variant_id: str) -> Path:
    return (
        config.component_dir
        / "data"
        / "variants"
        / str(variant_id)
        / config.template_basename
    )


def _window_loaded_variant(data: dict[str, Any], digest: str | None) -> _WindowLoadedVariant:
    loaded = _WindowLoadedVariant(data)
    setattr(loaded, _WINDOW_HASH_ATTR, digest)
    return loaded


def loaded_variant_sha256(template: object) -> str | None | object:
    """Zwróć hash zapisany przy wczytaniu wariantu albo znacznik braku."""

    return getattr(template, _WINDOW_HASH_ATTR, _MISSING)


def _install_per_window_load_patch() -> None:
    current = varmod.load_variant_into_editor
    if getattr(current, "_giclee_writer_window_baseline", False):
        return

    def load_variant_for_window(config: Any, variant_id: str) -> dict[str, Any]:
        data = current(config, variant_id)
        digest = ws._hash_path(_variant_path(config, variant_id))
        return _window_loaded_variant(dict(data), digest)

    setattr(load_variant_for_window, "_giclee_writer_window_baseline", True)
    setattr(load_variant_for_window, "__wrapped__", current)
    varmod.load_variant_into_editor = load_variant_for_window


def persist_variant_for_window(
    config: Any,
    variant_id: str,
    template: dict[str, Any],
    *,
    expected_sha256: str | None,
) -> ws.VariantWriteResult:
    """Zapisz wariant tylko gdy odpowiada hashowi tego konkretnego okna."""

    path = _variant_path(config, variant_id)
    before = ws._read_bytes(path)
    before_hash = ws._sha256_bytes(before) if before is not None else None
    if before_hash != expected_sha256:
        raise RuntimeError(
            "Wersja na dysku zmieniła się od momentu wczytania w tym oknie. "
            "Zamknij lub odśwież to okno przed ponownym zapisem."
        )

    # Baza powstaje dopiero po poprawnej kontroli stale state i zachowuje
    # dokładne bajty widziane przez to okno przed pierwszym zapisem.
    delta._ensure_base(config, variant_id, before)

    after = ws._json_bytes(template)
    after_hash = ws._sha256_bytes(after)
    if before == after:
        return ws.VariantWriteResult(
            path=path,
            changed=False,
            before_sha256=before_hash,
            after_sha256=after_hash,
            backup_path=None,
        )

    backup: Path | None = None
    if before is not None:
        output = ws.PlannedOutput(
            path=path,
            before_bytes=before,
            after_bytes=after,
            before_sha256=before_hash,
            after_sha256=after_hash,
            backup_label=path.stem,
        )
        backup = ws._write_exact_backup(
            config,
            variant_id,
            output,
            category="variant_backups",
        )

    ws._atomic_write(path, after)
    return ws.VariantWriteResult(
        path=path,
        changed=True,
        before_sha256=before_hash,
        after_sha256=after_hash,
        backup_path=backup,
    )


def _run_window_safe_variant_save(context: ws._EditorContext) -> None:
    variant_id = str(context.state.get("variant_id") or "")
    if not variant_id:
        messagebox.showerror(
            context.config.app_title,
            "Brak aktywnej wersji.",
            parent=context.host,
        )
        return

    expected = loaded_variant_sha256(context.state.get("template"))
    if expected is _MISSING:
        messagebox.showerror(
            context.config.app_title,
            "Brak hasha wariantu przypisanego do tego okna. "
            "Zamknij i ponownie otwórz komponent przed zapisem.",
            parent=context.host,
        )
        return

    pending = delta.build_minimal_variant_from_state(context.config, context.state)
    if not delta._confirm_minimal_save(context, pending):
        return

    try:
        result = persist_variant_for_window(
            context.config,
            variant_id,
            pending,
            expected_sha256=expected,
        )
    except Exception as exc:
        messagebox.showerror(
            context.config.app_title,
            str(exc),
            parent=context.host,
        )
        return

    loaded = _window_loaded_variant(dict(pending), result.after_sha256)
    context.state["template"] = loaded
    context.state["baseline_template"] = copy.deepcopy(loaded)
    context.state["zone_values"] = {
        zone.zone_id: load_zone_values(loaded, zone)
        for zone in context.config.zones
    }
    context.state["dirty"] = False
    if context.refresh_zone_list is not None:
        context.refresh_zone_list()

    label = varmod.variant_label(context.config, variant_id)
    if context.status_var is not None:
        context.status_var.set(
            f"Zapisano wersję «{label}». Plik motywu nie został zmieniony."
        )
    ws.show_toast(context.host, f"Zapisano wersję {label}.")


@dataclass(frozen=True)
class SourceSnapshot:
    role: str
    path: Path
    bytes: bytes
    sha256: str


@dataclass(frozen=True)
class LockedApplyPlan(ws.ApplyPlan):
    source_snapshots: tuple[SourceSnapshot, ...] = ()


def _template_from_bytes(raw_bytes: bytes, path: Path) -> dict[str, Any]:
    raw = raw_bytes.decode("utf-8")
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end < 0:
            raise ValueError(f"Nieprawidłowy nagłówek JSON: {path}")
        raw = raw[end + 2 :]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} — nieprawidłowy format.")
    return data


def _source_snapshot(role: str, path: Path) -> SourceSnapshot:
    raw = ws._read_bytes(path)
    if raw is None:
        raise FileNotFoundError(f"Brak źródła Apply ({role}): {path}")
    return SourceSnapshot(
        role=role,
        path=path,
        bytes=raw,
        sha256=ws._sha256_bytes(raw),
    )


def build_locked_delta_apply_plan(
    config: Any,
    variant_id: str,
    *,
    theme_path: Path | None = None,
    include_effects_asset: bool = True,
) -> LockedApplyPlan:
    """Zbuduj deltę z dokładnych, zamrożonych bajtów motywu i źródeł."""

    path = Path(theme_path) if theme_path is not None else template_path_for_config(config)
    before = ws._read_bytes(path)
    if before is None:
        raise FileNotFoundError(f"Brak pliku motywu: {path}")

    base_path = delta._base_path(config, variant_id)
    variant_path = _variant_path(config, variant_id)
    base_source = _source_snapshot("baza wariantu", base_path)
    variant_source = _source_snapshot("wariant", variant_path)

    current_theme = _template_from_bytes(before, path)
    base = _template_from_bytes(base_source.bytes, base_source.path)
    variant = _template_from_bytes(variant_source.bytes, variant_source.path)
    merged = delta.merge_variant_delta(config, current_theme, base, variant)
    after = ws._theme_bytes(path, merged)

    outputs: list[ws.PlannedOutput] = [
        ws.PlannedOutput(
            path=path,
            before_bytes=before,
            after_bytes=after,
            before_sha256=ws._sha256_bytes(before),
            after_sha256=ws._sha256_bytes(after),
            backup_label=path.stem,
        )
    ]

    if include_effects_asset:
        sections = ws.export_section_effects_for_front(config, variant_id)
        if sections:
            effects = ws._effects_output(config, variant_id)
            if effects is not None:
                outputs.append(effects)

    changed = [output for output in outputs if output.before_bytes != output.after_bytes]
    diff_parts = [ws._diff_for_output(output) for output in changed]
    diff_text = "\n\n".join(part for part in diff_parts if part.strip())
    if not diff_text:
        diff_text = "Brak zmian względem aktualnych plików motywu."

    return LockedApplyPlan(
        config=config,
        variant_id=str(variant_id),
        outputs=tuple(outputs),
        diff_text=diff_text,
        source_snapshots=(base_source, variant_source),
    )


def _assert_source_unchanged(source: SourceSnapshot) -> None:
    current = ws._read_bytes(source.path)
    current_hash = ws._sha256_bytes(current) if current is not None else None
    if current_hash != source.sha256:
        raise RuntimeError(
            f"Źródło Apply zmieniło się po utworzeniu podglądu ({source.role}):\n"
            f"{source.path}\nUtwórz nowy podgląd i spróbuj ponownie."
        )


def _snapshot(plan: LockedApplyPlan, role: str) -> SourceSnapshot:
    for source in plan.source_snapshots:
        if source.role == role:
            return source
    raise RuntimeError(f"Plan Apply nie zawiera źródła: {role}")


def _rollback_outputs(plan: LockedApplyPlan) -> list[str]:
    errors: list[str] = []
    for output in reversed(plan.changed_outputs):
        try:
            ws._restore_output(output)
        except Exception as exc:  # pragma: no cover - awaria systemu plików
            errors.append(f"{output.path}: {exc}")
    return errors


def apply_locked_delta_plan(
    plan: ws.ApplyPlan,
    *,
    confirmation: str,
) -> tuple[Path, ...]:
    """Zastosuj plan tylko dla niezmienionych źródeł i spójnie przesuń bazę."""

    if not isinstance(plan, LockedApplyPlan):
        return _core_apply(plan, confirmation=confirmation)

    expected_phrase = f"ZASTOSUJ {plan.variant_id}"
    if confirmation.strip() != expected_phrase:
        raise ValueError(f"Wymagana fraza: {expected_phrase}")

    for source in plan.source_snapshots:
        _assert_source_unchanged(source)

    base_source = _snapshot(plan, "baza wariantu")
    variant_source = _snapshot(plan, "wariant")
    targets_written = False
    base_written = False

    try:
        paths = _core_apply(plan, confirmation=confirmation)
        targets_written = True

        # Źródła są sprawdzane także po zapisie celów. Jeżeli zmieniły się
        # w trakcie operacji, cele zostaną cofnięte do bajtów z podglądu.
        for source in plan.source_snapshots:
            _assert_source_unchanged(source)

        ws._atomic_write(base_source.path, variant_source.bytes)
        base_written = True

        # Baza musi odpowiadać dokładnie wariantowi użytemu do preview, nie
        # nowszej zawartości odczytanej już po Apply.
        _assert_source_unchanged(variant_source)
        return paths
    except Exception as exc:
        rollback_errors: list[str] = []
        if base_written:
            try:
                ws._atomic_write(base_source.path, base_source.bytes)
            except Exception as restore_exc:  # pragma: no cover
                rollback_errors.append(f"{base_source.path}: {restore_exc}")
        if targets_written:
            rollback_errors.extend(_rollback_outputs(plan))
        if rollback_errors:
            raise RuntimeError(
                "Apply nie powiódł się, a automatyczne wycofanie było niepełne:\n"
                + "\n".join(rollback_errors)
            ) from exc
        raise


def install_concurrency_fix() -> None:
    """Zainstaluj per-window save i source-locked delta Apply."""

    # Najpierw instalujemy bazową warstwę, aby wrapper wczytywania wariantu był
    # najwyższą, idempotentną warstwą i nie mnożył się przy kolejnych oknach.
    ws.install_writer_safety()
    _install_per_window_load_patch()
    ws._run_variant_only_save = _run_window_safe_variant_save
    ws.build_bounded_apply_plan = build_locked_delta_apply_plan
    ws.apply_bounded_plan = apply_locked_delta_plan
    delta.build_delta_apply_plan = build_locked_delta_apply_plan
    delta.apply_delta_plan = apply_locked_delta_plan


__all__ = [
    "LockedApplyPlan",
    "SourceSnapshot",
    "apply_locked_delta_plan",
    "build_locked_delta_apply_plan",
    "install_concurrency_fix",
    "loaded_variant_sha256",
    "persist_variant_for_window",
]
