"""Classify exact transient Tcl/Tk runtime failures in Stage 2 pytest output.

The classifier is intentionally narrow. It does not retry arbitrary Tk failures,
application exceptions, test assertions, or dependency errors.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_TCL_ERROR = re.compile(r"(?:_?tkinter\.TclError|TclError:)", re.IGNORECASE)
_USABLE_RUNTIME = re.compile(
    r"can't find a usable\s+(?:init|tk)\.tcl\b",
    re.IGNORECASE,
)
_UNREADABLE_RUNTIME = re.compile(
    r"couldn['’]t read file[^\r\n]*(?:init|tk)\.tcl\b",
    re.IGNORECASE,
)


def is_transient_tcl_runtime_output(text: str) -> bool:
    """Return true only for known hosted-runner Tcl/Tk file-read failures."""

    if not _TCL_ERROR.search(text):
        return False
    return bool(_USABLE_RUNTIME.search(text) or _UNREADABLE_RUNTIME.search(text))


def classify_file(path: Path) -> bool:
    """Read a pytest text report and classify it without raising on encoding."""

    return is_transient_tcl_runtime_output(
        path.read_text(encoding="utf-8", errors="replace")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    print("true" if classify_file(args.report) else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
