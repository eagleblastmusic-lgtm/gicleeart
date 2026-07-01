#!/usr/bin/env python3
"""Test wysylki Resend (ten sam adres co Worker). Wymaga RESEND_API_KEY w cursor-api/.env."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
env_path = ROOT / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
if not api_key:
    print("Brak RESEND_API_KEY w cursor-api/.env — skopiuj klucz z panelu Resend.")
    sys.exit(1)

to = "gicleeartpl@gmail.com"
payload = {
    "from": "Giclee Art <onboarding@resend.dev>",
    "to": [to],
    "subject": "Test Giclee mockup worker",
    "html": "<p>Test wysylki z scripts/test_resend.py</p>",
}

req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "GicleeApp/1.0 (test_resend)",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("Resend OK", resp.status, resp.read().decode("utf-8", errors="replace"))
except urllib.error.HTTPError as e:
    print("Resend BLAD", e.code, e.read().decode("utf-8", errors="replace"))
    sys.exit(1)
