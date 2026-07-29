from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

CEST = timezone(timedelta(hours=2))
# All GicleeArt history for today
day_start = datetime(2026, 7, 29, 0, 0, tzinfo=CEST).timestamp() * 1000
day_end = datetime(2026, 7, 29, 23, 59, tzinfo=CEST).timestamp() * 1000
hist = Path(r"C:\Users\Skarabeusz\AppData\Roaming\Cursor\User\History")
rows = []
for entries_path in hist.glob("*/entries.json"):
    try:
        data = json.loads(entries_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    resource = data.get("resource", "")
    if "GicleeArt" not in resource:
        continue
    rel = resource.split("GicleeArt/")[-1] if "GicleeArt/" in resource else resource
    interesting = any(
        x in rel
        for x in (
            "quote-pin",
            "scroll-scrub",
            "media.liquid",
            "video_sequence",
            "gui.py",
            "page.filozofia",
            "wrota-parallax",
            "theme-inline",
            "registry",
        )
    )
    if not interesting:
        continue
    for e in data.get("entries", []):
        ts = e.get("timestamp", 0)
        if day_start <= ts <= day_end:
            dt = datetime.fromtimestamp(ts / 1000, tz=CEST).strftime("%H:%M:%S")
            rows.append((ts, dt, e.get("id", ""), rel, str(entries_path.parent)))

for item in sorted(rows):
    print(f"{item[1]}  {item[2]:24}  {item[3]}")
