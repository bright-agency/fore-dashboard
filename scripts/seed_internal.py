"""Local only: builds team/internal.dev.json from Windsor MCP dumps for previewing the team page.

Usage: py -I scripts/seed_internal.py <fx.json> name=dump.json [name=dump.json ...]
names as in fetch_internal.DATASETS. Never commit the output.
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
os.environ["INTERNAL_PLAIN"] = "1"
from common import DATA_FILE, fx_lookup  # noqa: E402
import internal  # noqa: E402
from fetch_internal import write_outputs  # noqa: E402

fx = fx_lookup({d: v["ILS"] for d, v in json.load(open(sys.argv[1], encoding="utf-8"))["rates"].items()})
raw = {}
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    raw[name] = json.load(open(path, encoding="utf-8"))["result"]
client = json.loads(DATA_FILE.read_text(encoding="utf-8"))
write_outputs(internal.build(client, raw, fx, datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(timespec="minutes")))
