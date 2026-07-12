"""Full tracked-tree audit based on the central repository data policy."""

from __future__ import annotations

import ast
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .policy import classify_path, normalize_repo_path


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)

_NAMED_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:[\"']?)(?:access_token|refresh_token|client_secret|api_key|password)"
    r"(?:[\"']?)\s*(?::|=(?!=))\s*(?P<expression>.+)$"
)

_PLACEHOLDER_SECRET_VALUES = frozenset(
    {
        "changeme",
        "change-me",
        "change_me",
        "dummy",
        "example",
        "example-secret",
        "not-a-secret",
        "password",
        "placeholder",
        "replace-me",
        "replace_me",
        "secret",
        "test-password",
        "test-secret",
        "your-api-key",
        "your-password",
        "your_api_key",
        "your_password",
    }
)

PII_KEYS = frozenset(
    {
        "client",
        "customer",
        "customer_name",
        "email",
        "e-mail",
        "address",
        "street",
        "postal_code",
        "phone",
        "telefon",
        "nip",
    }
)

TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".pyw",
        ".json",
        ".jsonl",
        ".csv",
        ".tsv",
        ".txt",
        ".md",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".js",
        ".mjs",
        ".ts",
        ".tsx",
        ".html",
        ".liquid",
        ".css",
        ".scss",
        ".xml",
        ".ps1",
        ".bat",
        ".sh",
    }
)

DATA_SUFFIXES = frozenset({".json", ".jsonl", ".csv", ".tsv"})
APPROVED_LARGE_BINARY_PREFIXES = (
    "giclee_app/assets/",
    "Komponenty/",
    "docs/review-demos/",
    "lightroom-giclee-crop/",
)
APPROVED_BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf", ".otf"}
)


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    rule_id: str
    path: str
    message: str
    line: int | None = None


@dataclass
class TrackedTreeAuditReport:
    repo_root: str
    tracked_files: int = 0
    findings: list[AuditFinding] = field(default_factory=list)
    classified_counts: dict[str, int] = field(default_factory=dict)
    error: str = ""

    @property
    def blockers(self) -> list[AuditFinding]:
        return [finding for finding in self.findings if finding.severity == "BLOCKER"]

    @property
    def warnings(self) -> list[AuditFinding]:
        return [finding for finding in self.findings if finding.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.error and not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_root": self.repo_root,
            "tracked_files": self.tracked_files,
            "ok": self.ok,
            "error": self.error,
            "classified_counts": dict(sorted(self.classified_counts.items())),
            "blocker_count": len(self.blockers),
            "warning_count": len(self.warnings),
            "findings": [asdict(finding) for finding in self.findings],
        }

    def format_text(self) -> str:
        lines = [
            "=== Repository tracked-tree audit ===",
            f"Repository: {self.repo_root}",
            f"Tracked files: {self.tracked_files}",
            f"Blockers: {len(self.blockers)}",
            f"Warnings: {len(self.warnings)}",
        ]
        if self.error:
            lines.append(f"ERROR: {self.error}")
        if self.classified_counts:
            lines.append("Classifications:")
            for key, value in sorted(self.classified_counts.items()):
                lines.append(f"  {key}: {value}")
        if self.findings:
            lines.append("Findings:")
            for finding in self.findings:
                location = finding.path
                if finding.line is not None:
                    location += f":{finding.line}"
                lines.append(
                    f"  [{finding.severity}] {finding.rule_id} {location} — {finding.message}"
                )
        return "\n".join(lines) + "\n"


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )


def list_tracked_files(repo_root: Path) -> list[str]:
    proc = _run_git(repo_root, ["ls-files", "-z"])
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or "git ls-files failed")
    return sorted(
        normalize_repo_path(raw.decode("utf-8", errors="surrogateescape"))
        for raw in proc.stdout.split(b"\0")
        if raw
    )


def _is_test_or_example(path: str) -> bool:
    lower = path.lower()
    name = Path(lower).name
    return (
        lower.startswith("tests/")
        or "/tests/" in lower
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".example." in lower
        or ".sample." in lower
        or lower.endswith((".example", ".sample"))
    )


def _read_text_for_scan(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _quoted_literal(expression: str) -> str | None:
    candidate = expression.lstrip()
    if not candidate or candidate[0] not in {"'", '"'}:
        return None
    quote = candidate[0]
    escaped = False
    for index, char in enumerate(candidate[1:], 1):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char != quote:
            continue
        token = candidate[: index + 1]
        try:
            value = ast.literal_eval(token)
        except (SyntaxError, ValueError):
            return None
        return value if isinstance(value, str) else None
    return None


def _looks_like_real_literal_secret(value: str) -> bool:
    normalized = value.strip().lower()
    if len(normalized) < 8:
        return False
    if normalized in _PLACEHOLDER_SECRET_VALUES:
        return False
    if normalized.startswith(("${", "{{", "<")) and normalized.endswith(("}", ">")):
        return False
    if normalized.startswith(("env:", "process.env", "os.environ")):
        return False
    return True


def _inside_quoted_context(line: str, offset: int) -> bool:
    active_quote: str | None = None
    escaped = False
    for char in line[:offset]:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if active_quote is None:
            if char in {"'", '"'}:
                active_quote = char
            continue
        if char == active_quote:
            active_quote = None
    return active_quote is not None


def _named_literal_secret_label(line: str) -> str | None:
    match = _NAMED_SECRET_ASSIGNMENT.search(line)
    if not match or _inside_quoted_context(line, match.start()):
        return None
    literal = _quoted_literal(match.group("expression"))
    if literal is None or not _looks_like_real_literal_secret(literal):
        return None
    return "NAMED_SECRET_LITERAL"


def _secret_findings(rel: str, text: str) -> Iterable[AuditFinding]:
    if _is_test_or_example(rel):
        return ()
    findings: list[AuditFinding] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        strong_labels = [label for label, pattern in SECRET_PATTERNS if pattern.search(line)]
        labels = strong_labels or ([label] if (label := _named_literal_secret_label(line)) else [])
        for label in labels:
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    "SECRET_CONTENT",
                    rel,
                    f"Potential secret detected ({label}).",
                    line_no,
                )
            )
    return findings


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", value.strip().lower()).strip("_")


def _pii_findings(rel: str, text: str) -> Iterable[AuditFinding]:
    if _is_test_or_example(rel) or Path(rel).suffix.lower() not in DATA_SUFFIXES:
        return ()

    found: set[str] = set()
    suffix = Path(rel).suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            first_line = text.splitlines()[0] if text.splitlines() else ""
            header = next(csv.reader([first_line], delimiter=delimiter), [])
        except (csv.Error, StopIteration):
            header = []
        found.update(key for key in map(_normalize_header, header) if key in PII_KEYS)
    else:
        for key in PII_KEYS:
            if re.search(rf'(?i)["\']{re.escape(key)}["\']\s*:', text):
                found.add(key)

    if not found:
        return ()
    return (
        AuditFinding(
            "BLOCKER",
            "PII_DATA_COLUMNS",
            rel,
            "Potential personal/customer data fields: " + ", ".join(sorted(found)),
        ),
    )


def _large_binary_finding(rel: str, path: Path, max_binary_bytes: int) -> AuditFinding | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= max_binary_bytes:
        return None
    suffix = path.suffix.lower()
    approved = suffix in APPROVED_BINARY_SUFFIXES and any(
        rel.startswith(prefix) for prefix in APPROVED_LARGE_BINARY_PREFIXES
    )
    if approved:
        return None
    return AuditFinding(
        "BLOCKER",
        "UNAPPROVED_LARGE_BINARY",
        rel,
        f"Tracked file is {size} bytes; threshold is {max_binary_bytes} bytes.",
    )


def audit_tracked_tree(
    repo_root: Path,
    *,
    max_text_scan_bytes: int = 2 * 1024 * 1024,
    max_binary_bytes: int = 10 * 1024 * 1024,
) -> TrackedTreeAuditReport:
    root = repo_root.resolve()
    report = TrackedTreeAuditReport(repo_root=str(root))
    try:
        tracked = list_tracked_files(root)
    except RuntimeError as exc:
        report.error = str(exc)
        return report

    report.tracked_files = len(tracked)
    for rel in tracked:
        decision = classify_path(rel)
        key = decision.classification.value if decision.classification else "UNCLASSIFIED"
        report.classified_counts[key] = report.classified_counts.get(key, 0) + 1

        if rel == "10.0.0" or Path(rel).name == "10.0.0":
            report.findings.append(
                AuditFinding(
                    "BLOCKER",
                    "ACCIDENTAL_ARTIFACT_10_0_0",
                    rel,
                    "Known accidental artifact name must not be tracked.",
                )
            )

        if not decision.tracked_allowed:
            report.findings.append(
                AuditFinding(
                    "BLOCKER",
                    decision.rule_id,
                    rel,
                    decision.reason,
                )
            )

        file_path = root / rel
        if not file_path.is_file():
            report.findings.append(
                AuditFinding(
                    "WARNING",
                    "TRACKED_FILE_MISSING_FROM_WORKTREE",
                    rel,
                    "Path is tracked but missing from the current worktree.",
                )
            )
            continue

        large_finding = _large_binary_finding(rel, file_path, max_binary_bytes)
        if large_finding is not None:
            report.findings.append(large_finding)

        suffix = file_path.suffix.lower()
        if suffix not in TEXT_SUFFIXES and file_path.name not in {
            ".gitignore",
            ".gitattributes",
            "Makefile",
        }:
            continue
        text = _read_text_for_scan(file_path, max_text_scan_bytes)
        if text is None:
            continue
        report.findings.extend(_secret_findings(rel, text))
        report.findings.extend(_pii_findings(rel, text))

    report.findings.sort(
        key=lambda item: (0 if item.severity == "BLOCKER" else 1, item.path, item.rule_id, item.line or 0)
    )
    return report


def write_json_report(report: TrackedTreeAuditReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
