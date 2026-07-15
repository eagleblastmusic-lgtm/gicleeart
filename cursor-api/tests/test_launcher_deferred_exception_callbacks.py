"""Regresja: callbacki Tk nie mogą zamykać zmiennych wyjątków z ``except``."""

from __future__ import annotations

import ast
from pathlib import Path


_LAUNCHER_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"


def _lambda_loaded_names(node: ast.Lambda) -> set[str]:
    bound = {
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    }
    if node.args.vararg is not None:
        bound.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        bound.add(node.args.kwarg.arg)
    return {
        child.id
        for child in ast.walk(node.body)
        if isinstance(child, ast.Name)
        and isinstance(child.ctx, ast.Load)
        and child.id not in bound
    }


def test_deferred_callbacks_do_not_close_over_exception_targets() -> None:
    tree = ast.parse(_LAUNCHER_PATH.read_text(encoding="utf-8"))
    offenders: list[tuple[int, str]] = []

    for handler in (node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)):
        exception_name = handler.name
        if not exception_name:
            continue
        for statement in handler.body:
            for child in ast.walk(statement):
                if not isinstance(child, ast.Lambda):
                    continue
                if exception_name in _lambda_loaded_names(child):
                    offenders.append((child.lineno, exception_name))

    assert offenders == [], (
        "Deferred callback closes over an exception target that Python clears "
        f"after the except block: {offenders}"
    )
