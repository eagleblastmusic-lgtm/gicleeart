from __future__ import annotations

from pathlib import Path

path = Path(__file__).resolve().parents[2] / "cursor-api/Komponenty/produkcja/view.py"
text = path.read_text(encoding="utf-8")

replacements = {
    'f"Archiwa sa w: {_data_dir_path()}\\archive_YYYY.json.",': (
        'f"Archiwa sa w: {_data_dir_path() / \'archive_YYYY.json\'}.",'
    ),
    "- Mozesz backupowac/wersjonowac te pliki w git.": (
        "- Mozesz backupowac te pliki; nie sa wersjonowane w git."
    ),
}

for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one occurrence, found {count}: {old!r}")
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8", newline="\n")
print("Fixed production AppData UI copy.")
