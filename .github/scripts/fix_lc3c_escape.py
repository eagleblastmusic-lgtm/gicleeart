from pathlib import Path


path = Path(".github/scripts/apply_lc3c.py")
text = path.read_text(encoding="utf-8")
needle = '        "\\n    def ", 1'
replacement = '        "\\\\n    def ", 1'
count = text.count(needle)
if count != 2:
    raise RuntimeError(f"expected two LC-3C escape sites, found {count}")
path.write_text(text.replace(needle, replacement), encoding="utf-8")
