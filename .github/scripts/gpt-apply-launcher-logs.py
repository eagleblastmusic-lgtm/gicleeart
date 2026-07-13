from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    root = Path.cwd().resolve()
    path = root / "cursor-api" / "giclee_app" / "launcher.py"
    text = path.read_text(encoding="utf-8")

    marker = "from .launcher_logs import ("
    if marker in text:
        expected = [
            "_LOGS_DIR = DEFAULT_COMPONENT_LOGS_DIR",
            "def _component_log_write_path(self, comp: Component) -> Path:",
            "log_path = self._component_log_write_path(comp)",
        ]
        missing = [item for item in expected if item not in text]
        if missing:
            raise RuntimeError(f"launcher patch is partial; missing: {missing}")
        print("launcher.py already patched")
        return

    text = replace_once(
        text,
        "from .launcher_options import show_launcher_options\n",
        "from .launcher_options import show_launcher_options\n"
        "from .launcher_logs import (\n"
        "    DEFAULT_COMPONENT_LOGS_DIR,\n"
        "    component_log_read_path,\n"
        "    component_log_write_path,\n"
        ")\n",
        "launcher logs import",
    )
    text = replace_once(
        text,
        "_LOGS_DIR = Path(__file__).resolve().parents[1] / \"logs\"\n",
        "_LOGS_DIR = DEFAULT_COMPONENT_LOGS_DIR\n",
        "launcher logs directory",
    )
    text = replace_once(
        text,
        "    def _component_log_path(self, comp: Component) -> Path:\n"
        "        _LOGS_DIR.mkdir(parents=True, exist_ok=True)\n"
        "        return _LOGS_DIR / f\"{comp.folder_name}.log\"\n",
        "    def _component_log_path(self, comp: Component) -> Path:\n"
        "        return component_log_read_path(comp.folder_name, logs_dir=_LOGS_DIR)\n\n"
        "    def _component_log_write_path(self, comp: Component) -> Path:\n"
        "        return component_log_write_path(comp.folder_name, logs_dir=_LOGS_DIR)\n",
        "launcher log path methods",
    )
    text = replace_once(
        text,
        "    def _clear_component_log(self, comp: Component) -> None:\n"
        "        path = self._component_log_path(comp)\n",
        "    def _clear_component_log(self, comp: Component) -> None:\n"
        "        path = self._component_log_write_path(comp)\n",
        "launcher clear log path",
    )
    text = replace_once(
        text,
        "        log_path = self._component_log_path(comp)\n",
        "        log_path = self._component_log_write_path(comp)\n",
        "launcher append log path",
    )

    path.write_text(text, encoding="utf-8")
    print(f"patched {path.relative_to(root)}")


if __name__ == "__main__":
    main()
