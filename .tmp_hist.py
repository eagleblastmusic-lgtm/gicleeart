from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

CEST = timezone(timedelta(hours=2))
start = datetime(2026, 7, 29, 3, 40, tzinfo=CEST).timestamp() * 1000
end = datetime(2026, 7, 29, 5, 55, tzinfo=CEST).timestamp() * 1000
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
    for e in data.get("entries", []):
        ts = e.get("timestamp", 0)
        if start <= ts <= end:
            dt = datetime.fromtimestamp(ts / 1000, tz=CEST).strftime("%H:%M:%S")
            rows.append((ts, dt, e.get("id", ""), rel, str(entries_path.parent)))

for ts, dt, eid, rel, folder in sorted(rows):
    print(f"{dt}  {eid:24}  {rel}")
    print(f"         {folder}")
