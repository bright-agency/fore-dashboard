"""Daily refresh: pulls Meta, Google Ads and LinkedIn from the Windsor.ai REST API and rewrites data.json.

Needs env WINDSOR_API_KEY (GitHub secret). Run: python scripts/fetch_windsor.py
LinkedIn spend is in USD and is converted to ILS with the daily ECB rate (frankfurter.dev).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from common import (GOOGLE_ACCOUNT, campaign_status, HISTORY_START, LINKEDIN_ACCOUNT, META_ACCOUNT,  # noqa: E402
                    fx_lookup, google_row, linkedin_row, meta_row, presets, write_data)

API = "https://connectors.windsor.ai/{connector}"
KEY = os.environ.get("WINDSOR_API_KEY", "").strip()


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "fore-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


def get(connector: str, account: str, fields: list, date_from, date_to) -> list:
    qs = urllib.parse.urlencode({
        "api_key": KEY,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "fields": ",".join(fields),
        "select_accounts": account,
    })
    body = http_json(API.format(connector=connector) + "?" + qs)
    return body.get("data", []) if isinstance(body, dict) else body


def usd_ils(date_from, date_to):
    body = http_json(f"https://api.frankfurter.dev/v1/{(date_from - timedelta(days=7)).isoformat()}..{date_to.isoformat()}?from=USD&to=ILS")
    return fx_lookup({d: v["ILS"] for d, v in body["rates"].items()})


def reach_block(connector, account, field, a, b):
    by = get(connector, account, ["campaign", field], a, b)
    tot = get(connector, account, ["account_id", field], a, b)
    return {
        "total": int(sum(float(r.get(field) or 0) for r in tot)),
        "by": {r["campaign"]: int(float(r.get(field) or 0)) for r in by if r.get("campaign")},
    }


def main():
    if not KEY:
        sys.exit("WINDSOR_API_KEY is not set")
    now = datetime.now(ZoneInfo("Asia/Jerusalem"))
    as_of = (now - timedelta(days=1)).date()
    fx = usd_ils(HISTORY_START, as_of)

    meta = get("facebook", META_ACCOUNT,
               ["date", "campaign", "impressions", "link_clicks", "spend",
                "actions_onsite_conversion_lead_grouped"], HISTORY_START, as_of)
    google = get("google_ads", GOOGLE_ACCOUNT,
                 ["date", "campaign", "impressions", "clicks", "conversions", "cost"], HISTORY_START, as_of)
    linkedin = get("linkedin", LINKEDIN_ACCOUNT,
                   ["date", "campaign", "impressions", "clicks", "spend", "oneclickleads"], HISTORY_START, as_of)
    rows = ([meta_row(r) for r in meta] + [google_row(r) for r in google]
            + [linkedin_row(r, fx) for r in linkedin])

    # Reach is not additive across days, so it is fetched as a total for every fixed period.
    reach = {}
    for key, (a, b) in presets(as_of).items():
        reach[key] = {
            "meta": reach_block("facebook", META_ACCOUNT, "reach", a, b),
            "linkedin": reach_block("linkedin", LINKEDIN_ACCOUNT, "approximate_unique_impressions", a, b),
        }

    # Current campaign status (live / paused / ended)
    status = {
        "meta": {r["campaign"]: campaign_status(r.get("campaign_effective_status"), r.get("campaign_stop_time"), as_of)
                 for r in get("facebook", META_ACCOUNT, ["campaign", "campaign_effective_status", "campaign_stop_time"],
                              HISTORY_START, as_of) if r.get("campaign")},
        "google": {r["campaign"]: campaign_status(r.get("campaign_status"), None, as_of)
                   for r in get("google_ads", GOOGLE_ACCOUNT, ["campaign", "campaign_status"], HISTORY_START, as_of)
                   if r.get("campaign")},
        "linkedin": {r["campaign"]: campaign_status(r.get("campaign_status"), r.get("campaign_end_date"), as_of)
                     for r in get("linkedin", LINKEDIN_ACCOUNT, ["campaign", "campaign_status", "campaign_end_date"],
                                  HISTORY_START, as_of) if r.get("campaign")},
    }

    if not rows:
        sys.exit("Windsor returned no rows - keeping previous data.json")
    write_data(as_of, rows, reach, now.isoformat(timespec="minutes"), status)


if __name__ == "__main__":
    main()
