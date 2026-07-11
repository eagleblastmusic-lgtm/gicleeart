"""WS-1: bezpieczny zapis wariantów i jawne bounded apply do motywu.

Warstwa jest instalowana przez ``bootstrap.build_page_ui`` dla cienkich
komponentów Administracji strony. Zwykłe ``Zapisz wersję`` nie dotyka motywu,
assetów ani Shopify. Dopiero osobne ``Zastosuj wersję do motywu…`` wykonuje
kontrolowany merge pól zarządzanych przez ``config.zones``.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
import tkinter as tk
from typing import Any, Callable

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.stronaglowna.service import theme_root

from .config import PageEditorConfig
from . import gui_shell
from . import variants as varmod
from .page_section_effects_settings import (
    effects_asset_basename,
    export_section_effects_for_front,
    page_template_slug,
    zone_has_image_effects,
    zone_has_text_effects,
)
from .service_base import (
    INDEX_HEADER,
    apply_zone_values,
    load_template_from_path,
    load_zone_values,
    template_path_for_config,
)


@dataclass(frozen=True)
class VariantWriteResult:
    path: Path
    changed: bool
    before_sha256: str | None
    after_sha256: str
    backup_path: Path | None


@dataclass(frozen=True)
class PlannedOutput:
    path: Path
    before_bytes: bytes | None
    after_bytes: bytes
    before_sha256: str | None
    after_sha256: str
    backup_label: str


@dataclass(frozen=True)
class ApplyPlan:
    config: PageEditorConfig
    variant_id: str
    outputs: tuple[PlannedOutput, ...]
    diff_text: str

    @property
    def changed_outputs(self) -> tuple[PlannedOutput, ...]:
        return tuple(
            output
            for output in self.outputs
            if output.before_bytes != output.after_bytes
        )


@dataclass
class _EditorContext:
    host: tk.Misc
    config: PageEditorConfig
    state: dict[str, Any]
    status_var: tk.StringVar | None = None
    confirm_save: Callable[[str], dict[str, Any] | None] | None = None
    refresh_zone_list: Callable[[], None] | None = None


_VARIANT_BASELINES: dict[str, str | None] = {}
_BUILD_STACK: list[tuple[tk.Misc, PageEditorConfig]] = []
_PATCH_LOCK = threading.RLock()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _hash_path(path: Path) -> str | None:
    data = _read_bytes(path)
    return _sha256_bytes(data) if data is not None else None


def _variant_path(config: PageEditorConfig, variant_id: str) -> Path:
    return (
        config.component_dir
        / "data"
        / "variants"
        / str(variant_id)
        / config.template_basename
    )


def _variant_key(config: PageEditorConfig, variant_id: str) -> str:
    return str(_variant_path(config, variant_id).resolve()).casefold()


def _json_bytes(data: dict[str, Any], *, header: str = "") -> bytes:
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return (header + body).encode("utf-8")


def _theme_bytes(path: Path, data: dict[str, Any]) -> bytes:
    rel = str(path).replace("\\", "/")
    header = INDEX_HEADER if "/templates/" in rel else ""
    return _json_bytes(data, header=header)


def _write_temp(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return temp


def _atomic_write(path: Path, data: bytes) -> None:
    temp = _write_temp(path, data)
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


def _write_exact_backup(
    config: PageEditorConfig,
    variant_id: str,
    output: PlannedOutput,
    *,
    category: str,
) -> Path | None:
    if output.before_bytes is None:
        return None
    digest = (output.before_sha256 or "missing")[:12]
    root = config.component_dir / "data" / category / str(variant_id)
    root.mkdir(parents=True, exist_ok=True)
    suffix = output.path.suffix or ".bin"
    backup = root / (
        f"{output.backup_label}-before-{_timestamp()}-{digest}{suffix}"
    )
    backup.write_bytes(output.before_bytes)
    return backup


def record_variant_baseline(config: PageEditorConfig, variant_id: str) -> str | None:
    digest = _hash_path(_variant_path(config, variant_id))
    _VARIANT_BASELINES[_variant_key(config, variant_id)] = digest
    return digest


def safe_persist_editor_to_variant(
    config: PageEditorConfig,
    variant_id: str,
    template: dict[str, Any],
) -> VariantWriteResult:
    """Zapisz tylko wskazany wariant, atomowo i z ochroną stale state."""

    path = _variant_path(config, variant_id)
    key = _variant_key(config, variant_id)
    before = _read_bytes(path)
    before_hash = _sha256_bytes(before) if before is not None else None

    if key in _VARIANT_BASELINES:
        expected = _VARIANT_BASELINES[key]
        if before_hash != expected:
            raise RuntimeError(
                "Wersja na dysku zmieniła się od momentu wczytania. "
                "Odśwież lub ponownie otwórz komponent przed zapisem."
            )
    else:
        _VARIANT_BASELINES[key] = before_hash

    after = _json_bytes(template)
    after_hash = _sha256_bytes(after)
    if before == after:
        _VARIANT_BASELINES[key] = after_hash
        return VariantWriteResult(
            path=path,
            changed=False,
            before_sha256=before_hash,
            after_sha256=after_hash,
            backup_path=None,
        )

    backup: Path | None = None
    if before is not None:
        output = PlannedOutput(
            path=path,
            before_bytes=before,
            after_bytes=after,
            before_sha256=before_hash,
            after_sha256=after_hash,
            backup_label=path.stem,
        )
        backup = _write_exact_backup(
            config,
            variant_id,
            output,
            category="variant_backups",
        )

    _atomic_write(path, after)
    _VARIANT_BASELINES[key] = after_hash
    return VariantWriteResult(
        path=path,
        changed=True,
        before_sha256=before_hash,
        after_sha256=after_hash,
        backup_path=backup,
    )


def _zone_exists_in_variant(variant: dict[str, Any], zone: Any) -> bool:
    if bool(getattr(zone, "settings_only", False)):
        return True
    section_key = str(getattr(zone, "section_key", "") or "")
    if not section_key:
        return True
    sections = variant.get("sections")
    return isinstance(sections, dict) and isinstance(sections.get(section_key), dict)


def merge_managed_zones(
    config: PageEditorConfig,
    current_theme: dict[str, Any],
    variant: dict[str, Any],
) -> dict[str, Any]:
    """Zacznij od świeżego motywu i zastosuj tylko pola z config.zones."""

    merged = copy.deepcopy(current_theme)
    for zone in config.zones:
        if not _zone_exists_in_variant(variant, zone):
            continue
        values = load_zone_values(variant, zone)
        apply_zone_values(merged, zone, values)
    return merged


def _effects_output(config: PageEditorConfig, variant_id: str) -> PlannedOutput | None:
    if not any(
        zone_has_text_effects(zone) or zone_has_image_effects(zone)
        for zone in config.zones
    ):
        return None

    sections = export_section_effects_for_front(config, variant_id)
    payload = {
        "page": page_template_slug(config),
        "variant": variant_id,
        "sections": sections,
    }
    data = (
        "window.GICLEE_PAGE_SECTION_EFFECTS = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n"
    ).encode("utf-8")
    path = theme_root() / "assets" / effects_asset_basename(config)
    before = _read_bytes(path)
    return PlannedOutput(
        path=path,
        before_bytes=before,
        after_bytes=data,
        before_sha256=_sha256_bytes(before) if before is not None else None,
        after_sha256=_sha256_bytes(data),
        backup_label=f"asset-{path.stem}",
    )


def _diff_for_output(output: PlannedOutput) -> str:
    before = (output.before_bytes or b"").decode("utf-8", errors="replace")
    after = output.after_bytes.decode("utf-8", errors="replace")
    lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"{output.path} (przed)",
        tofile=f"{output.path} (po)",
        lineterm="",
    )
    return "\n".join(lines)


def build_bounded_apply_plan(
    config: PageEditorConfig,
    variant_id: str,
    *,
    theme_path: Path | None = None,
    include_effects_asset: bool = True,
) -> ApplyPlan:
    """Zbuduj preview bez zapisu i zapamiętaj hashe wszystkich celów."""

    path = Path(theme_path) if theme_path is not None else template_path_for_config(config)
    before = _read_bytes(path)
    if before is None:
        raise FileNotFoundError(f"Brak pliku motywu: {path}")

    current_theme = load_template_from_path(path)
    variant = varmod.load_variant_data(config, variant_id)
    merged = merge_managed_zones(config, current_theme, variant)
    after = _theme_bytes(path, merged)

    outputs: list[PlannedOutput] = [
        PlannedOutput(
            path=path,
            before_bytes=before,
            after_bytes=after,
            before_sha256=_sha256_bytes(before),
            after_sha256=_sha256_bytes(after),
            backup_label=path.stem,
        )
    ]

    if include_effects_asset:
        effects = _effects_output(config, variant_id)
        if effects is not None:
            outputs.append(effects)

    changed = [output for output in outputs if output.before_bytes != output.after_bytes]
    diff_parts = [_diff_for_output(output) for output in changed]
    diff_text = "\n\n".join(part for part in diff_parts if part.strip())
    if not diff_text:
        diff_text = "Brak zmian względem aktualnych plików motywu."

    return ApplyPlan(
        config=config,
        variant_id=str(variant_id),
        outputs=tuple(outputs),
        diff_text=diff_text,
    )


def _restore_output(output: PlannedOutput) -> None:
    if output.before_bytes is None:
        output.path.unlink(missing_ok=True)
    else:
        _atomic_write(output.path, output.before_bytes)


def apply_bounded_plan(plan: ApplyPlan, *, confirmation: str) -> tuple[Path, ...]:
    """Zastosuj zatwierdzony plan po ponownym sprawdzeniu hashy."""

    expected_phrase = f"ZASTOSUJ {plan.variant_id}"
    if confirmation.strip() != expected_phrase:
        raise ValueError(f"Wymagana fraza: {expected_phrase}")

    changed = plan.changed_outputs
    if not changed:
        return ()

    for output in changed:
        current_hash = _hash_path(output.path)
        if current_hash != output.before_sha256:
            raise RuntimeError(
                f"Plik zmienił się po utworzeniu podglądu:\n{output.path}\n"
                "Utwórz nowy podgląd i spróbuj ponownie."
            )

    for output in changed:
        _write_exact_backup(
            plan.config,
            plan.variant_id,
            output,
            category="apply_backups",
        )

    temps: dict[Path, Path] = {}
    replaced: list[PlannedOutput] = []
    try:
        for output in changed:
            temps[output.path] = _write_temp(output.path, output.after_bytes)
        for output in changed:
            os.replace(temps[output.path], output.path)
            replaced.append(output)
        return tuple(output.path for output in changed)
    except Exception:
        for output in reversed(replaced):
            try:
                _restore_output(output)
            except Exception:
                pass
        raise
    finally:
        for temp in temps.values():
            temp.unlink(missing_ok=True)


def _closure_values(function: Callable[..., Any]) -> dict[str, Any]:
    code = getattr(function, "__code__", None)
    cells = getattr(function, "__closure__", None) or ()
    if code is None:
        return {}
    out: dict[str, Any] = {}
    for name, cell in zip(code.co_freevars, cells):
        try:
            out[name] = cell.cell_contents
        except ValueError:
            continue
    return out


def _find_nested_callable(
    function: Callable[..., Any] | None,
    target_name: str,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> Callable[..., Any] | None:
    if not callable(function) or depth > 4:
        return None
    if getattr(function, "__name__", "") == target_name:
        return function
    seen = seen or set()
    if id(function) in seen:
        return None
    seen.add(id(function))
    for value in _closure_values(function).values():
        if callable(value):
            found = _find_nested_callable(
                value,
                target_name,
                depth=depth + 1,
                seen=seen,
            )
            if found is not None:
                return found
    return None


def _context_from_command(
    command: Callable[..., Any] | None,
    target_name: str,
    host: tk.Misc,
    config: PageEditorConfig,
) -> _EditorContext:
    target = _find_nested_callable(command, target_name)
    values = _closure_values(target) if target is not None else {}
    state = values.get("state")
    if not isinstance(state, dict):
        state = {}
    status_var = values.get("status_var")
    confirm_save = values.get("_confirm_save")
    refresh_zone_list = values.get("_refresh_zone_list")
    return _EditorContext(
        host=values.get("host") if isinstance(values.get("host"), tk.Misc) else host,
        config=values.get("config") if isinstance(values.get("config"), PageEditorConfig) else config,
        state=state,
        status_var=status_var if isinstance(status_var, tk.StringVar) else None,
        confirm_save=confirm_save if callable(confirm_save) else None,
        refresh_zone_list=refresh_zone_list if callable(refresh_zone_list) else None,
    )


def _run_variant_only_save(context: _EditorContext) -> None:
    if context.confirm_save is None:
        messagebox.showerror(
            context.config.app_title,
            "Nie udało się przygotować bezpiecznego zapisu wersji.",
            parent=context.host,
        )
        return

    pending = context.confirm_save("Zapisz wersję")
    if pending is None:
        return

    variant_id = str(context.state.get("variant_id") or "")
    try:
        varmod.persist_editor_to_variant(
            context.config,
            variant_id,
            pending,
        )
    except Exception as exc:
        messagebox.showerror(
            context.config.app_title,
            str(exc),
            parent=context.host,
        )
        return

    context.state["template"] = pending
    context.state["baseline_template"] = copy.deepcopy(pending)
    context.state["dirty"] = False
    if context.refresh_zone_list is not None:
        context.refresh_zone_list()

    label = varmod.variant_label(context.config, variant_id)
    if context.status_var is not None:
        context.status_var.set(
            f"Zapisano wersję «{label}». Plik motywu nie został zmieniony."
        )
    show_toast(context.host, f"Zapisano wersję {label}.")


def _open_apply_dialog(context: _EditorContext) -> None:
    if context.state.get("dirty"):
        messagebox.showwarning(
            context.config.app_title,
            "Najpierw kliknij «Zapisz wersję». "
            "Zastosowanie korzysta wyłącznie z zapisanej wersji na dysku.",
            parent=context.host,
        )
        return

    variant_id = str(context.state.get("variant_id") or "")
    try:
        plan = build_bounded_apply_plan(context.config, variant_id)
    except Exception as exc:
        messagebox.showerror(context.config.app_title, str(exc), parent=context.host)
        return

    win = tk.Toplevel(context.host)
    win.title("Zastosuj wersję do motywu — podgląd")
    position_toplevel_screen_center(win, 940, 650)
    win.transient(context.host)
    win.grab_set()

    label = varmod.variant_label(context.config, variant_id)
    ttk.Label(
        win,
        text=f"Wersja: {label} ({variant_id})",
        font=("", 10, "bold"),
        padding=(12, 10),
    ).pack(anchor="w")
    ttk.Label(
        win,
        text=(
            "Zmiany dotyczą wyłącznie pól zarządzanych przez ten komponent. "
            "Deploy nie zostanie uruchomiony."
        ),
        padding=(12, 0, 12, 8),
    ).pack(anchor="w")

    diff = scrolledtext.ScrolledText(win, wrap="none", font=("Consolas", 8))
    diff.pack(fill="both", expand=True, padx=12, pady=(0, 10))
    diff.insert("1.0", plan.diff_text)
    diff.configure(state="disabled")

    expected = f"ZASTOSUJ {variant_id}"
    confirm_row = ttk.Frame(win, padding=(12, 0, 12, 8))
    confirm_row.pack(fill="x")
    ttk.Label(confirm_row, text=f"Wpisz: {expected}").pack(side="left")
    confirmation_var = tk.StringVar()
    ttk.Entry(confirm_row, textvariable=confirmation_var, width=32).pack(
        side="left", padx=(8, 0)
    )

    def do_apply() -> None:
        try:
            paths = apply_bounded_plan(
                plan,
                confirmation=confirmation_var.get(),
            )
        except Exception as exc:
            messagebox.showerror(context.config.app_title, str(exc), parent=win)
            return

        if context.status_var is not None:
            if paths:
                context.status_var.set(
                    f"Zastosowano wersję «{label}» do motywu. Deploy: nie."
                )
            else:
                context.status_var.set(
                    f"Wersja «{label}» nie wymagała zmian w motywie."
                )
        win.destroy()
        if paths:
            messagebox.showinfo(
                context.config.app_title,
                "Zastosowano wersję do plików motywu.\n"
                "Utworzono kopie zapasowe. Deploy nie został uruchomiony.",
                parent=context.host,
            )
        else:
            messagebox.showinfo(
                context.config.app_title,
                "Brak zmian do zastosowania.",
                parent=context.host,
            )

    buttons = ttk.Frame(win, padding=(12, 0, 12, 12))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Anuluj", command=win.destroy).pack(side="right")
    ttk.Button(buttons, text="Zastosuj", command=do_apply).pack(
        side="right", padx=(0, 8)
    )


def _open_deploy_only(context: _EditorContext) -> None:
    warning = (
        "Deploy wdroży wyłącznie aktualny stan plików motywu na dysku.\n\n"
        "Nie zapisze ani nie zastosuje aktualnie edytowanej wersji."
    )
    if context.state.get("dirty"):
        warning += "\n\nW edytorze są niezapisane zmiany wersji."
    if not messagebox.askyesno(
        context.config.app_title,
        warning + "\n\nKontynuować do wyboru środowiska?",
        parent=context.host,
    ):
        return

    picker = tk.Toplevel(context.host)
    picker.title("Wdróż motyw — bez zapisu")
    position_toplevel_screen_center(picker, 560, 320)
    picker.transient(context.host)
    picker.grab_set()

    target_var = tk.StringVar(value="development")
    for key, meta in gui_shell.DEPLOY_TARGETS.items():
        ttk.Radiobutton(
            picker,
            text=str(meta.get("label", key)),
            value=key,
            variable=target_var,
        ).pack(anchor="w", padx=16, pady=4)

    log_box = scrolledtext.ScrolledText(picker, height=9, font=("Consolas", 8))
    log_box.pack(fill="both", expand=True, padx=12, pady=8)

    def start() -> None:
        key = target_var.get()
        meta = gui_shell.DEPLOY_TARGETS.get(key, {})
        if key == "live" and not messagebox.askyesno(
            context.config.app_title,
            "Wdróż aktualny stan dysku na LIVE?",
            parent=picker,
        ):
            return

        log_box.insert("end", f"Deploy bez zapisu: {meta.get('label', key)}\n")
        log_box.update_idletasks()

        def worker() -> None:
            try:
                code = gui_shell.deploy_theme(
                    environment=str(meta.get("environment", key)),
                    allow_live=bool(meta.get("allow_live")),
                    on_line=lambda line: context.host.after(
                        0,
                        lambda value=line: log_box.insert("end", value + "\n"),
                    ),
                )
                if context.status_var is not None:
                    context.host.after(
                        0,
                        lambda: context.status_var.set(
                            f"Deploy zakończony (kod {code}); bez zapisu wersji."
                        ),
                    )
            except Exception as exc:
                context.host.after(
                    0,
                    lambda: messagebox.showerror(
                        context.config.app_title,
                        str(exc),
                        parent=picker,
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(picker, text="Wdróż", command=start).pack(
        side="right", padx=12, pady=8
    )
    ttk.Button(picker, text="Zamknij", command=picker.destroy).pack(
        side="right", pady=8
    )


def _ensure_apply_button(
    master: tk.Misc,
    context: _EditorContext,
    ttk_module: Any,
) -> None:
    if getattr(master, "_giclee_writer_apply_button", False):
        return
    setattr(master, "_giclee_writer_apply_button", True)
    button = ttk_module.Button(
        master,
        text="Zastosuj wersję do motywu…",
        command=lambda: _open_apply_dialog(context),
    )
    button.pack(side="right", padx=(0, 8))


class _WriterSafetyTtkProxy:
    _giclee_writer_safety_proxy = True

    def __init__(self, ttk_module: Any) -> None:
        self._ttk = ttk_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ttk, name)

    def Button(
        self,
        master: tk.Misc | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> ttk.Widget:
        text = str(kwargs.get("text") or "")
        command = kwargs.get("command")
        build = _BUILD_STACK[-1] if _BUILD_STACK else None

        if build is not None and callable(command) and text == "Zapisz":
            host, config = build
            context = _context_from_command(
                command,
                "_save_all",
                host,
                config,
            )
            kwargs["text"] = "Zapisz wersję"
            kwargs["command"] = lambda: _run_variant_only_save(context)
            widget = self._ttk.Button(master, *args, **kwargs)
            if master is not None:
                master.after_idle(
                    lambda m=master, c=context: _ensure_apply_button(
                        m,
                        c,
                        self._ttk,
                    )
                )
            return widget

        if build is not None and callable(command) and text == "Wdróż motyw…":
            host, config = build
            context = _context_from_command(
                command,
                "_deploy",
                host,
                config,
            )
            kwargs["command"] = lambda: _open_deploy_only(context)

        return self._ttk.Button(master, *args, **kwargs)


def _install_variant_io_patch() -> None:
    current_load = varmod.load_variant_into_editor
    if not getattr(current_load, "_giclee_writer_safety", False):

        def load_variant_with_baseline(
            config: PageEditorConfig,
            variant_id: str,
        ) -> dict[str, Any]:
            data = current_load(config, variant_id)
            record_variant_baseline(config, variant_id)
            return data

        setattr(load_variant_with_baseline, "_giclee_writer_safety", True)
        setattr(load_variant_with_baseline, "__wrapped__", current_load)
        varmod.load_variant_into_editor = load_variant_with_baseline

    current_persist = varmod.persist_editor_to_variant
    if not getattr(current_persist, "_giclee_writer_safety", False):

        def persist_variant_safely(
            config: PageEditorConfig,
            variant_id: str,
            template: dict[str, Any],
        ) -> None:
            safe_persist_editor_to_variant(config, variant_id, template)

        setattr(persist_variant_safely, "_giclee_writer_safety", True)
        setattr(persist_variant_safely, "__wrapped__", current_persist)
        varmod.persist_editor_to_variant = persist_variant_safely


def install_writer_safety() -> None:
    with _PATCH_LOCK:
        _install_variant_io_patch()
        current = gui_shell.ttk
        if not getattr(current, "_giclee_writer_safety_proxy", False):
            gui_shell.ttk = _WriterSafetyTtkProxy(current)


def _add_variant_safety_hint(host: tk.Misc) -> None:
    if getattr(host, "_giclee_writer_safety_hint", False):
        return

    def walk(widget: tk.Misc):
        for child in widget.winfo_children():
            yield child
            yield from walk(child)

    for widget in walk(host):
        if not isinstance(widget, ttk.Combobox):
            continue
        parent = widget.master
        if getattr(parent, "_giclee_writer_safety_hint", False):
            return
        ttk.Label(
            parent,
            text=(
                "Edycja wersji nie zmienia motywu, dopóki nie użyjesz "
                "«Zastosuj wersję do motywu…»."
            ),
            foreground="#666",
        ).pack(side="left", padx=(12, 0))
        setattr(parent, "_giclee_writer_safety_hint", True)
        setattr(host, "_giclee_writer_safety_hint", True)
        return


def build_safe_page_editor(
    host: tk.Misc,
    config: PageEditorConfig,
    *,
    inline: bool = False,
) -> None:
    install_writer_safety()
    _BUILD_STACK.append((host, config))
    try:
        gui_shell.build_page_editor(host, config, inline=inline)
    finally:
        _BUILD_STACK.pop()
    host.after_idle(lambda: _add_variant_safety_hint(host))


__all__ = [
    "ApplyPlan",
    "VariantWriteResult",
    "apply_bounded_plan",
    "build_bounded_apply_plan",
    "build_safe_page_editor",
    "install_writer_safety",
    "merge_managed_zones",
    "record_variant_baseline",
    "safe_persist_editor_to_variant",
]
