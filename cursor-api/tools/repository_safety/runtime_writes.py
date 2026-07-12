"""Diagnostic inventory of Python writes rooted in the source checkout.

The scanner is intentionally review-oriented. It does not change the tracked-tree
audit baseline and does not block CI unless the caller explicitly asks for
``--fail-on-findings``. Its job is to identify write calls whose target is
derived from ``__file__`` so Runtime Foundation work can migrate them to
``giclee_app.app_paths`` in small, verified packages.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .audit import list_tracked_files


_SCANNED_PREFIXES = (
    "Komponenty/",
    "giclee_app/",
    "cursor-api/Komponenty/",
    "cursor-api/giclee_app/",
)
_SAFE_PATH_FACTORIES = frozenset(
    {
        "AppPath",
        "backup_path",
        "cache_path",
        "config_path",
        "data_path",
        "log_path",
    }
)
_DIRECT_PATH_METHODS = frozenset(
    {
        "mkdir",
        "open",
        "rename",
        "replace",
        "rmdir",
        "touch",
        "unlink",
        "write_bytes",
        "write_text",
    }
)
_KNOWN_PATH_CALLS: dict[str, tuple[int, ...]] = {
    "atomic_write_bytes": (0,),
    "atomic_write_text": (0,),
    "os.makedirs": (0,),
    "os.mkdir": (0,),
    "os.remove": (0,),
    "os.rename": (0, 1),
    "os.replace": (0, 1),
    "os.rmdir": (0,),
    "os.unlink": (0,),
    "shutil.copy": (1,),
    "shutil.copy2": (1,),
    "shutil.copyfile": (1,),
    "shutil.copytree": (1,),
    "shutil.move": (0, 1),
    "shutil.rmtree": (0,),
}
_WRITER_NAME = re.compile(
    r"(?i)(?:^|_)(?:append|copy|dump|export|move|persist|rename|replace|save|store|write)(?:_|$)"
)
_WRITE_MODES = frozenset({"a", "w", "x", "+"})


@dataclass(frozen=True)
class RuntimeWriteFinding:
    path: str
    line: int
    rule_id: str
    call: str
    source_symbols: tuple[str, ...]
    message: str


@dataclass
class RuntimeWriteReport:
    repo_root: str
    scanned_files: int = 0
    parse_errors: list[str] = field(default_factory=list)
    findings: list[RuntimeWriteFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.parse_errors and not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_root": self.repo_root,
            "scanned_files": self.scanned_files,
            "ok": self.ok,
            "parse_errors": list(self.parse_errors),
            "finding_count": len(self.findings),
            "findings": [asdict(item) for item in self.findings],
        }

    def format_text(self) -> str:
        lines = [
            "=== Runtime source-write inventory ===",
            f"Repository: {self.repo_root}",
            f"Scanned Python files: {self.scanned_files}",
            f"Parse errors: {len(self.parse_errors)}",
            f"Review findings: {len(self.findings)}",
        ]
        for error in self.parse_errors:
            lines.append(f"  [PARSE] {error}")
        for finding in self.findings:
            symbols = ", ".join(finding.source_symbols) or "__file__"
            lines.append(
                f"  [REVIEW] {finding.rule_id} {finding.path}:{finding.line} "
                f"{finding.call} [{symbols}] — {finding.message}"
            )
        return "\n".join(lines) + "\n"


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _target_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for item in node.elts:
            names.update(_target_names(item))
        return names
    return set()


def _scope_nodes(body: list[ast.stmt]) -> Iterable[ast.AST]:
    """Yield nodes in one lexical scope, excluding nested functions/classes."""

    stack: list[ast.AST] = list(reversed(body))
    while stack:
        node = stack.pop()
        yield node
        children = list(ast.iter_child_nodes(node))
        for child in reversed(children):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.append(child)


def _source_symbols(node: ast.AST | None, rooted: set[str], *, assignment: bool = False) -> set[str]:
    if node is None:
        return set()
    if assignment and isinstance(node, ast.Call):
        name = _dotted_name(node.func).rsplit(".", 1)[-1]
        if name in _SAFE_PATH_FACTORIES:
            return set()

    symbols: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            if child.id == "__file__":
                symbols.add("__file__")
            elif child.id in rooted:
                symbols.add(child.id)
    return symbols


def _rooted_names(body: list[ast.stmt], inherited: set[str]) -> set[str]:
    rooted = set(inherited)
    assignments: list[tuple[set[str], ast.AST]] = []

    for node in _scope_nodes(body):
        if isinstance(node, ast.Assign):
            targets: set[str] = set()
            for target in node.targets:
                targets.update(_target_names(target))
            assignments.append((targets, node.value))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            assignments.append((_target_names(node.target), node.value))
        elif isinstance(node, ast.NamedExpr):
            assignments.append((_target_names(node.target), node.value))

    changed = True
    while changed:
        changed = False
        for targets, value in assignments:
            if not targets or not _source_symbols(value, rooted, assignment=True):
                continue
            missing = targets - rooted
            if missing:
                rooted.update(missing)
                changed = True
    return rooted


def _literal_mode(call: ast.Call, *, default: str = "r") -> str:
    node: ast.AST | None = None
    if len(call.args) >= 2:
        node = call.args[1]
    for keyword in call.keywords:
        if keyword.arg == "mode":
            node = keyword.value
    if node is None:
        return default
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _is_write_mode(mode: str) -> bool:
    return bool(mode) and any(flag in mode for flag in _WRITE_MODES)


def _call_path_arguments(call: ast.Call, dotted: str) -> tuple[ast.AST, ...]:
    positions = _KNOWN_PATH_CALLS.get(dotted)
    if positions is None:
        positions = _KNOWN_PATH_CALLS.get(dotted.rsplit(".", 1)[-1])
    if positions is None:
        return ()
    return tuple(call.args[index] for index in positions if index < len(call.args))


def _finding(
    *,
    rel: str,
    call: ast.Call,
    rule_id: str,
    call_name: str,
    symbols: set[str],
    message: str,
) -> RuntimeWriteFinding:
    return RuntimeWriteFinding(
        path=rel,
        line=getattr(call, "lineno", 0),
        rule_id=rule_id,
        call=call_name,
        source_symbols=tuple(sorted(symbols)),
        message=message,
    )


def _scan_scope(rel: str, body: list[ast.stmt], inherited: set[str]) -> list[RuntimeWriteFinding]:
    rooted = _rooted_names(body, inherited)
    findings: list[RuntimeWriteFinding] = []

    for node in _scope_nodes(body):
        if not isinstance(node, ast.Call):
            continue

        dotted = _dotted_name(node.func)
        short = dotted.rsplit(".", 1)[-1]
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None

        if short in _DIRECT_PATH_METHODS and receiver is not None:
            symbols = _source_symbols(receiver, rooted)
            if symbols:
                if short == "open" and not _is_write_mode(_literal_mode(node)):
                    continue
                findings.append(
                    _finding(
                        rel=rel,
                        call=node,
                        rule_id="DIRECT_SOURCE_PATH_WRITE",
                        call_name=dotted or short,
                        symbols=symbols,
                        message="Direct filesystem mutation targets a path derived from the source checkout.",
                    )
                )
                continue

        if dotted in {"open", "builtins.open"}:
            if not node.args or not _is_write_mode(_literal_mode(node)):
                continue
            symbols = _source_symbols(node.args[0], rooted)
            if symbols:
                findings.append(
                    _finding(
                        rel=rel,
                        call=node,
                        rule_id="DIRECT_SOURCE_PATH_WRITE",
                        call_name=dotted,
                        symbols=symbols,
                        message="Writable open() targets a path derived from the source checkout.",
                    )
                )
                continue

        path_args = _call_path_arguments(node, dotted)
        symbols: set[str] = set()
        for argument in path_args:
            symbols.update(_source_symbols(argument, rooted))
        if symbols:
            findings.append(
                _finding(
                    rel=rel,
                    call=node,
                    rule_id="SOURCE_PATH_PASSED_TO_WRITER",
                    call_name=dotted or short,
                    symbols=symbols,
                    message="A known writer receives a path derived from the source checkout.",
                )
            )
            continue

        if short in _SAFE_PATH_FACTORIES or not _WRITER_NAME.search(short):
            continue

        symbols = set()
        for argument in node.args:
            symbols.update(_source_symbols(argument, rooted))
        for keyword in node.keywords:
            symbols.update(_source_symbols(keyword.value, rooted))
        if symbols:
            findings.append(
                _finding(
                    rel=rel,
                    call=node,
                    rule_id="SOURCE_PATH_PASSED_TO_WRITER",
                    call_name=dotted or short,
                    symbols=symbols,
                    message="A write-like helper receives a path derived from the source checkout.",
                )
            )

    for statement in body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(_scan_scope(rel, statement.body, rooted))
        elif isinstance(statement, ast.ClassDef):
            findings.extend(_scan_scope(rel, statement.body, rooted))
    return findings


def scan_python_source(rel: str, text: str) -> tuple[list[RuntimeWriteFinding], str]:
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as exc:
        return [], f"{rel}:{exc.lineno or 0}: {exc.msg}"
    findings = _scan_scope(rel, tree.body, set())
    unique = {
        (item.path, item.line, item.rule_id, item.call, item.source_symbols): item
        for item in findings
    }
    return sorted(unique.values(), key=lambda item: (item.path, item.line, item.rule_id, item.call)), ""


def audit_runtime_writes(repo_root: Path) -> RuntimeWriteReport:
    root = repo_root.resolve()
    report = RuntimeWriteReport(repo_root=str(root))
    for rel in list_tracked_files(root):
        if not rel.endswith(".py") or not rel.startswith(_SCANNED_PREFIXES):
            continue
        path = root / rel
        if not path.is_file():
            continue
        report.scanned_files += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.parse_errors.append(f"{rel}: {exc}")
            continue
        findings, error = scan_python_source(rel, text)
        report.findings.extend(findings)
        if error:
            report.parse_errors.append(error)

    report.parse_errors.sort()
    report.findings.sort(key=lambda item: (item.path, item.line, item.rule_id, item.call))
    return report


def write_runtime_write_json(report: RuntimeWriteReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "RuntimeWriteFinding",
    "RuntimeWriteReport",
    "audit_runtime_writes",
    "scan_python_source",
    "write_runtime_write_json",
]
