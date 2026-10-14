"""Daily refresh: pulls Meta + Google Ads from the Windsor.ai REST API and rewrites data.json.

Needs env WINDSOR_API_KEY (GitHub secret). Run: python scripts/fetch_windsor.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from common import (GOOGLE_ACCOUNT, HISTORY_START, META_ACCOUNT, google_row,  # noqa: E402
                    meta_row, presets, write_data)

API = "https://connectors.windsor.ai/{connector}"
KEY = os.environ.get("WINDSOR_API_KEY", "").strip()


def get(connector: str, account: str, fields: list, date_from, date_to) -> list:
    qs = urllib.parse.urlencode({
        "api_key": KEY,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "fields": ",".join(fields),
        "select_accounts": account,
    })
    with urllib.request.urlopen(API.format(connector=connector) + "?" + qs, timeout=180) as resp:
        body = json.load(resp)
    return body.get("data", []) if isinstance(body, dict) else body


def main():
    if not KEY:
        sys.exit("WINDSOR_API_KEY is not set")
    now = datetime.now(ZoneInfo("Asia/Jerusalem"))
    as_of = (now - timedelta(days=1)).date()

    meta = get("facebook", META_ACCOUNT,
               ["date", "campaign", "impressions", "link_clicks", "spend",
                "actions_onsite_conversion_lead_grouped"], HISTORY_START, as_of)
    google = get("google_ads", GOOGLE_ACCOUNT,
                 ["date", "campaign", "impressions", "clicks", "conversions", "cost"], HISTORY_START, as_of)
    rows = [meta_row(r) for r in meta] + [google_row(r) for r in google]

    # Reach is not additive across days, so it is fetched as a total for every fixed period.
    reach = {}
    for key, (a, b) in presets(as_of).items():
        by = get("facebook", META_ACCOUNT, ["campaign", "reach"], a, b)
        tot = get("facebook", META_ACCOUNT, ["account_id", "reach"], a, b)
        reach[key] = {
            "total": int(sum(float(r.get("reach") or 0) for r in tot)),
            "by": {r["campaign"]: int(float(r.get("reach") or 0)) for r in by if r.get("campaign")},
        }

    if not rows:
        sys.exit("Windsor returned no rows - keeping previous data.json")
    write_data(as_of, rows, reach, now.isoformat(timespec="minutes"))


if __name__ == "__main__":
    main()
