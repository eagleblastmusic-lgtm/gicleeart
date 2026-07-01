#!/usr/bin/env python3
"""Szybki test Resend GET /emails (nagłówki quota)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.limity.collectors import collect_resend

sec = collect_resend()
print("status:", sec.status, sec.error or "")
for m in sec.meters:
    print(m.title, m.used, "/", m.quota)
