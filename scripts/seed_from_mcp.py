"""One-off: builds data.json from Windsor MCP dumps (used before the API key secret exists).

Usage: py -I scripts/seed_from_mcp.py <google_dump.json> <meta_dump.json> <as_of YYYY-MM-DD>
"""
import json
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from common import google_row, meta_row, write_data  # noqa: E402

g, m, as_of = sys.argv[1], sys.argv[2], date.fromisoformat(sys.argv[3])
load = lambda p: json.load(open(p, encoding="utf-8"))["result"]
rows = [google_row(r) for r in load(g)] + [meta_row(r) for r in load(m)]
reach = json.load(open(os.path.join(os.path.dirname(__file__), "reach_seed.json"), encoding="utf-8"))
write_data(as_of, rows, reach, datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(timespec="minutes"))
