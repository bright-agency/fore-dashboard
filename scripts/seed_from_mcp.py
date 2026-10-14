"""One-off: builds data.json from Windsor MCP dumps (used before the API key secret exists).

Usage: py -I scripts/seed_from_mcp.py <google.json> <meta.json> <linkedin.json> <fx.json> <as_of YYYY-MM-DD>
"""
import json
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from common import fx_lookup, google_row, linkedin_row, meta_row, write_data  # noqa: E402

g, m, li, fxp, as_of = sys.argv[1:6]
load = lambda p: json.load(open(p, encoding="utf-8"))["result"]
fx = fx_lookup({d: v["ILS"] for d, v in json.load(open(fxp, encoding="utf-8"))["rates"].items()})
rows = ([google_row(r) for r in load(g)] + [meta_row(r) for r in load(m)]
        + [linkedin_row(r, fx) for r in load(li)])
seed = json.load(open(os.path.join(os.path.dirname(__file__), "reach_seed.json"), encoding="utf-8"))
li_tot = seed.pop("_linkedin_totals")
reach = {k: {"meta": v, "linkedin": {"total": li_tot[k], "by": {}}} for k, v in seed.items()}
write_data(date.fromisoformat(as_of), rows, reach, datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(timespec="minutes"))
