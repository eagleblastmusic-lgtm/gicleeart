"""Kontrakt LC-1: jawny composition root klasycznego launchera."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app import launcher
from giclee_app import category_launcher
from giclee_app import dragdrop_category_launcher
from giclee_app import options_category_launcher
from giclee_app import styled_category_launcher


class _FakeRoot:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def withdraw(self) -> None:
        self._events.append("withdraw")

    def deiconify(self) -> None:
        self._events.append("deiconify")

    def mainloop(self) -> None:
        self._events.append("mainloop")


def _install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> _FakeRoot:
    root = _FakeRoot(events)
    fake_tkdnd = SimpleNamespace(TkinterDnD=SimpleNamespace(Tk=lambda: root))
    monkeypatch.setitem(sys.modules, "tkinterdnd2", fake_tkdnd)

    from giclee_app import splash_screen

    def run_splash_then(_root: object, callback: Callable[[], None]) -> None:
        events.append("splash")
        callback()

    monkeypatch.setattr(splash_screen, "run_splash_then", run_splash_then)
    return root


def test_final_launcher_mro_is_unchanged() -> None:
    assert dragdrop_category_launcher.DragDropCategoryGicleeApp.__mro__ == (
        dragdrop_category_launcher.DragDropCategoryGicleeApp,
        options_category_launcher.OptionsCategoryGicleeApp,
        styled_category_launcher.StyledCategoryGicleeApp,
        category_launcher.CategoryGicleeApp,
        launcher.GicleeApp,
        object,
    )


@pytest.mark.parametrize(
    ("module", "expected_factory"),
    [
        (category_launcher, category_launcher.CategoryGicleeApp),
        (styled_category_launcher, styled_category_launcher.StyledCategoryGicleeApp),
        (options_category_launcher, options_category_launcher.OptionsCategoryGicleeApp),
        (dragdrop_category_launcher, dragdrop_category_launcher.DragDropCategoryGicleeApp),
    ],
)
def test_layer_entrypoints_pass_factory_without_runtime_class_replacement(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    expected_factory: object,
) -> None:
    captured: list[object] = []
    original_class = launcher.GicleeApp

    def fake_main(*, app_factory: object = None) -> None:
        captured.append(app_factory)

    monkeypatch.setattr(module._launcher, "main", fake_main)
    module.main()

    assert captured == [expected_factory]
    assert launcher.GicleeApp is original_class


@pytest.mark.parametrize(
    "filename",
    [
        "category_launcher.py",
        "styled_category_launcher.py",
        "options_category_launcher.py",
        "dragdrop_category_launcher.py",
    ],
)
def test_layer_sources_do_not_assign_launcher_class(filename: str) -> None:
    source = (Path(__file__).resolve().parents[1] / "giclee_app" / filename).read_text(
        encoding="utf-8"
    )
    assert "_launcher.GicleeApp =" not in source
    assert "original_class = _launcher.GicleeApp" not in source
    assert "_launcher.main(app_factory=" in source


def test_launcher_main_uses_explicit_factory_once_after_splash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    launcher.main(app_factory=factory)

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_launcher_main_defaults_to_base_launcher_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def base_factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    monkeypatch.setattr(launcher, "GicleeApp", base_factory)
    launcher.main()

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_package_main_targets_canonical_launcher_app_entrypoint() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "giclee_app" / "__main__.py"
    ).read_text(encoding="utf-8")
    assert "from .launcher_app import main" in source
    assert "dragdrop_category_launcher" not in source
    assert "studio_preview" not in source


def test_launcher_uses_background_services_scheduler_and_no_direct_calls() -> None:
    # 1. Sprawdzenie, czy launcher.py importuje LauncherBackgroundServices
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")
    assert "from .launcher_background_services import LauncherBackgroundServices" in source

    # 2. Sprawdzenie braku bezpośrednich wywołań w launcher.py przy starcie
    assert "self.root.after(1500, self._check_monthly_reminder)" not in source
    assert "self.root.after(800, self._check_monthly_plan_reminder)" not in source
    assert "self.root.after(30_000, self._poll_orders_from_shopify)" not in source
    assert "self.root.after(35_000, self._poll_accounting_orders)" not in source
    assert "self.root.after(2000, self._run_daily_backup)" not in source
    assert "self.root.after(15_000, self._check_cure_done_notifications)" not in source
    assert "self.root.after(45_000, self._poll_cykl_publisher)" not in source
    assert "self.root.after(3000, self._check_cykl_weekly_reminder)" not in source


def test_no_trailing_after_calls_in_worker_methods_ast() -> None:
    # 5. Wykrywanie braku historycznych recurring calli w metodach cyklicznych przez AST
    import ast
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    tree = ast.parse(launcher_path.read_text(encoding="utf-8"))

    methods_to_check = {
        "_auto_rescan": ("_auto_rescan", 3000),
        "_poll_orders_from_shopify": ("_poll_orders_from_shopify", 300000),
        "_poll_accounting_orders": ("_poll_accounting_orders", 300000),
        "_check_cure_done_notifications": ("_check_cure_done_notifications", 60000),
        "_poll_cykl_publisher": ("_poll_cykl_publisher", 60000),
    }

    found_methods = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in methods_to_check:
            found_methods += 1
            cb_name, expected_delay = methods_to_check[node.name]

            # Wyszukajmy wywołania after w tej metodzie
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    is_after = False
                    if isinstance(child.func, ast.Attribute) and child.func.attr == "after":
                        is_after = True

                    if is_after:
                        # Sprawdzamy delay
                        if child.args:
                            delay_node = child.args[0]
                            try:
                                delay_val = ast.literal_eval(delay_node)
                            except ValueError:
                                if isinstance(delay_node, ast.BinOp):
                                    def eval_binop(op_node: ast.expr) -> int:
                                        if isinstance(op_node, ast.Constant):
                                            return int(op_node.value)
                                        if isinstance(op_node, ast.BinOp):
                                            left = eval_binop(op_node.left)
                                            right = eval_binop(op_node.right)
                                            if isinstance(op_node.op, ast.Mult):
                                                return left * right
                                        return 0
                                    delay_val = eval_binop(delay_node)
                                else:
                                    delay_val = -1

                            # Zezwalamy tylko na delay == 0 (UI dispatch)
                            if delay_val != 0:
                                if len(child.args) > 1:
                                    cb_arg = child.args[1]
                                    cb_str = ast.unparse(cb_arg)
                                    assert cb_name not in cb_str, f"Found trailing recurring after call in {node.name}"

    assert found_methods == 5


def test_launcher_background_services_integration_in_init_ast() -> None:
    # 6. Dokładna weryfikacja integracji w GicleeApp.__init__ za pomocą AST
    import ast
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    tree = ast.parse(launcher_path.read_text(encoding="utf-8"))

    init_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            init_node = node
            break

    assert init_node is not None

    build_ui_idx = -1
    refresh_idx = -1
    scheduler_creation_idx = -1
    scheduler_start_idx = -1
    creation_call_node = None

    for idx, stmt in enumerate(init_node.body):
        stmt_str = ast.unparse(stmt)
        if "self._build_ui()" in stmt_str:
            build_ui_idx = idx
        elif "self._refresh_components()" in stmt_str:
            refresh_idx = idx
        elif "LauncherBackgroundServices(" in stmt_str:
            scheduler_creation_idx = idx
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                creation_call_node = stmt.value
        elif "self._background_services.start()" in stmt_str:
            scheduler_start_idx = idx

    assert build_ui_idx != -1
    assert refresh_idx != -1
    assert scheduler_creation_idx != -1
    assert scheduler_start_idx != -1

    # Kolejność wywołań
    assert build_ui_idx < refresh_idx
    assert refresh_idx < scheduler_creation_idx
    assert scheduler_creation_idx < scheduler_start_idx

    # Wywołane dokładnie raz
    source = launcher_path.read_text(encoding="utf-8")
    assert source.count("LauncherBackgroundServices(") == 1
    assert source.count("._background_services.start()") == 1

    # Parametry
    assert creation_call_node is not None
    assert len(creation_call_node.args) == 1
    assert ast.unparse(creation_call_node.args[0]) == "self.root.after"

    expected_keywords = [
        ("auto_rescan", "self._auto_rescan"),
        ("monthly_reminder", "self._check_monthly_reminder"),
        ("monthly_plan_reminder", "self._check_monthly_plan_reminder"),
        ("shopify_orders", "self._poll_orders_from_shopify"),
        ("accounting_orders", "self._poll_accounting_orders"),
        ("daily_backup", "self._run_daily_backup"),
        ("cure_notifications", "self._check_cure_done_notifications"),
        ("social_publisher", "self._poll_cykl_publisher"),
        ("weekly_content_reminder", "self._check_cykl_weekly_reminder"),
    ]

    assert len(creation_call_node.keywords) == len(expected_keywords)
    for i, kw in enumerate(creation_call_node.keywords):
        name, val = expected_keywords[i]
        assert kw.arg == name
        assert ast.unparse(kw.value) == val


def test_daemon_threads_per_method_ast() -> None:
    # 7. Dokładna weryfikacja daemon threads za pomocą AST
    import ast
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    tree = ast.parse(launcher_path.read_text(encoding="utf-8"))

    expected_methods = {
        "_run_daily_backup": "_worker",
        "_check_cure_done_notifications": "_worker",
        "_poll_orders_from_shopify": "_worker",
        "_poll_accounting_orders": "_worker",
        "_poll_cykl_publisher": "_worker",
        "_launch": "self._watch_proc",
    }

    found_methods = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in expected_methods:
            found_methods += 1
            target_name = expected_methods[node.name]

            thread_calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func_str = ast.unparse(child.func)
                    if "Thread" in func_str:
                        has_daemon_true = False
                        for kw in child.keywords:
                            if kw.arg == "daemon" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                has_daemon_true = True
                        if has_daemon_true:
                            thread_calls.append(child)

            assert len(thread_calls) == 1, f"Expected exactly 1 daemon thread in {node.name}"
            call = thread_calls[0]
            target_node = None
            for kw in call.keywords:
                if kw.arg == "target":
                    target_node = kw.value
            assert target_node is not None
            assert target_name in ast.unparse(target_node)

    assert found_methods == 6


def test_excluded_timers_exact_calls_exist_in_launcher() -> None:
    # 8. Ochrona timerów wyłączonych z LC-5
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = launcher_path.read_text(encoding="utf-8")

    # 1. Canvas focus in _build_ui()
    assert "self.root.after_idle(self._focus_tiles_canvas)" in source
    # 2. Frame-timed wheel controller remains scheduled by Tk.
    assert "schedule=self.root.after" in source
    assert "self._wheel_scroll.add_delta(delta)" in source
    # 3. Generator delay 500 ms in _open_zadania_generator()
    assert "self.root.after(500, lambda: open_tasks_generator(self.root, on_saved=lambda _n: None))" in source
    # 4. Log preview win.after(2000, _auto) in _show_component_log()
    assert "win.after(2000, _auto)" in source
    # 5. UI dispatch calls in workers (after(0, ...))
    assert "self.root.after(0, lambda: self.status_var.set(" in source
    assert "self.root.after(0, lambda: show_toast(" in source


def test_studio_does_not_import_background_services_ast() -> None:
    # 9. Sprawdzenie braku importów schedulera przez Studio
    studio_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    assert studio_path.is_file()

    source = studio_path.read_text(encoding="utf-8")
    assert "launcher_background_services" not in source
    assert "LauncherBackgroundServices" not in source


def test_lazy_imports_exist_inside_worker_methods_ast() -> None:
    # 4. Weryfikacja lazy imports Komponenty wewnątrz metod GicleeApp przez AST
    import ast
    launcher_path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    tree = ast.parse(launcher_path.read_text(encoding="utf-8"))

    # 4.5. Brak top-level importów Komponenty
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module:
                assert not node.module.startswith("Komponenty")
        elif isinstance(node, ast.Import):
            for name in node.names:
                assert not name.name.startswith("Komponenty")

    # 4.1. Znajdź dokładnie klasę GicleeApp
    giclee_app_class = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "GicleeApp":
            giclee_app_class = node
            break
    assert giclee_app_class is not None

    # Bezpośrednie metody klasy
    direct_methods = {
        method.name: method
        for method in giclee_app_class.body
        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    expected_lc5_methods = {
        "_check_monthly_plan_reminder",
        "_open_zadania_generator",
        "_check_monthly_reminder",
        "_open_monthly_generator",
        "_run_daily_backup",
        "_check_cure_done_notifications",
        "_poll_orders_from_shopify",
        "_poll_accounting_orders",
        "_poll_cykl_publisher",
        "_check_cykl_weekly_reminder",
    }

    # 4.2. Exact target method existence
    for name in expected_lc5_methods:
        assert name in direct_methods

    # 4.3. Exact import ownership per metoda
    imports_by_method = {}
    for name in expected_lc5_methods:
        method_node = direct_methods[name]
        method_imports = set()
        for child in ast.walk(method_node):
            if isinstance(child, ast.ImportFrom):
                if child.module and child.module.startswith("Komponenty"):
                    method_imports.add(child.module)
            elif isinstance(child, ast.Import):
                for n in child.names:
                    if n.name.startswith("Komponenty"):
                        method_imports.add(n.name)
        imports_by_method[name] = method_imports

    assert set(imports_by_method.keys()) == expected_lc5_methods
    assert all(imports_by_method[name] for name in expected_lc5_methods)

    # 4.4. Dokładniejsze zamrożenie modułów
    # 1. _check_monthly_plan_reminder -> Komponenty.zadania
    assert "Komponenty.zadania" in imports_by_method["_check_monthly_plan_reminder"]
    # 2. _open_zadania_generator -> Komponenty.zadania.generator_zadan
    assert "Komponenty.zadania.generator_zadan" in imports_by_method["_open_zadania_generator"]
    # 3. _check_monthly_reminder -> Komponenty.zadania
    assert "Komponenty.zadania" in imports_by_method["_check_monthly_reminder"]
    # 4. _open_monthly_generator -> Komponenty.zadania.generator_zadan
    assert "Komponenty.zadania.generator_zadan" in imports_by_method["_open_monthly_generator"]
    # 5. _run_daily_backup -> Komponenty._shared
    assert any(m.startswith("Komponenty._shared") for m in imports_by_method["_run_daily_backup"])
    # 6. _check_cure_done_notifications -> Komponenty._shared.notifications
    assert "Komponenty._shared.notifications" in imports_by_method["_check_cure_done_notifications"]
    # 7. _poll_orders_from_shopify -> Komponenty.produkcja
    assert any(m.startswith("Komponenty.produkcja") for m in imports_by_method["_poll_orders_from_shopify"])
    # 8. _poll_accounting_orders -> Komponenty.dokumentysprzedazy.orders_sync
    assert any("dokumentysprzedazy" in m for m in imports_by_method["_poll_accounting_orders"])
    # 9. _poll_cykl_publisher -> Komponenty.socialmedia.cykl
    assert "Komponenty.socialmedia.cykl" in imports_by_method["_poll_cykl_publisher"]
    # 10. _check_cykl_weekly_reminder -> Komponenty.socialmedia.cykl
    assert "Komponenty.socialmedia.cykl" in imports_by_method["_check_cykl_weekly_reminder"]
