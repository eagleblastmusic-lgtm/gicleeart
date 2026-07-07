"""Headless smoke for 6G.5-M runtime marker verification.

Run from cursor-api/:
    py -3 scripts/smoke_6g5m_runtime_verify.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

LOG_PATH = ROOT / "giclee_app" / "logs" / "studio_perf.log"
os.environ["GICLEE_STUDIO_PERF"] = "1"
for env_name in (
    "GICLEE_STUDIO_IDLE_PREWARM",
    "GICLEE_ASSET_LAB_AUTO_FULL_CARDS",
):
    os.environ.pop(env_name, None)

if LOG_PATH.exists():
    LOG_PATH.unlink()

import customtkinter as ctk

from giclee_app.ui.gicleeframe_view import GicleeFrameView

root = ctk.CTk()
root.withdraw()
try:
    view = GicleeFrameView(root)
    view.pack()
    for _ in range(8):
        root.update()
        time.sleep(0.05)
finally:
    root.destroy()

if not LOG_PATH.exists():
    print("FAIL: studio_perf.log not created")
    sys.exit(1)

events: list[dict] = []
for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
    if line.strip():
        events.append(json.loads(line))

names = [e.get("event") for e in events]
marker = next((e for e in events if e.get("event") == "studio.gicleeframe.runtime_marker"), None)
print(json.dumps(marker, ensure_ascii=False, indent=2))
print("--- event order (first 20) ---")
for name in names[:20]:
    print(name)

checks = {
    "phase_marker_6G5M": marker and marker.get("phase_marker") == "6G.5-M",
    "module_file_ok": marker and "gicleeframe_view.py" in str(marker.get("module_file", "")),
    "has_schedule_true": marker and marker.get("has_schedule_init_refresh_light") is True,
    "has_event_true": marker and marker.get("has_init_refresh_light_scheduled_event") is True,
    "light_scheduled_logged": "studio.gicleeframe.init_refresh.light_scheduled" in names,
    "inventory_before_light_scheduled": False,
}
if "studio.gicleeframe.init_refresh.light_scheduled" in names:
    light_idx = names.index("studio.gicleeframe.init_refresh.light_scheduled")
    inv_idx = names.index("studio.gicleeframe.inventory.load_report") if "studio.gicleeframe.inventory.load_report" in names else -1
    checks["inventory_before_light_scheduled"] = inv_idx >= 0 and inv_idx < light_idx

print("--- checks ---")
for key, ok in checks.items():
    print(f"{key}: {'PASS' if ok else 'FAIL'}")

all_pass = all(
    checks[k]
    for k in (
        "phase_marker_6G5M",
        "module_file_ok",
        "has_schedule_true",
        "has_event_true",
        "light_scheduled_logged",
    )
) and not checks["inventory_before_light_scheduled"]

print("VERDICT:", "RUNTIME M OK" if all_pass else "RUNTIME STILL MISMATCH")
sys.exit(0 if all_pass else 1)
