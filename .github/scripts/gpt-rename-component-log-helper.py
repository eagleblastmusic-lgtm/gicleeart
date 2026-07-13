from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path.cwd().resolve()
    path = root / "cursor-api" / "giclee_app" / "launcher.py"
    text = path.read_text(encoding="utf-8")

    old = "from .launcher_logs import ("
    new = "from .component_logs import ("

    if new in text:
        if old in text:
            raise RuntimeError("launcher.py contains both old and new helper imports")
        print("launcher.py already uses component_logs")
        return

    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one launcher_logs import, found {count}")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {path.relative_to(root)}")


if __name__ == "__main__":
    main()
