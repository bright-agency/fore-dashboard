"""Shared helpers: period presets, name normalisation and data.json assembly."""
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

# Per-client settings live in scripts/client.json (copy this repo + edit it for a new client).
CONFIG = json.loads((Path(__file__).resolve().parent / "client.json").read_text(encoding="utf-8"))
META_ACCOUNT = CONFIG["accounts"]["meta"]
GOOGLE_ACCOUNT = CONFIG["accounts"]["google"]
LINKEDIN_ACCOUNT = CONFIG["accounts"]["linkedin"]   # billed in USD
HISTORY_START = date.fromisoformat(CONFIG["history_start"])

_INVISIBLE = re.compile(r"[‎‏‪-‮⁦-⁩﻿]")


def clean(name: str) -> str:
    return re.sub(r"\s+", " ", _INVISIBLE.sub("", name or "")).strip()


def presets(as_of: date) -> dict:
    """Fixed periods, all ending at as_of (last full day). Must mirror index.html."""
    first_this = as_of.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    q_start_month = ((as_of.month - 1) // 3) * 3 + 1
    q_start = date(as_of.year, q_start_month, 1)
    prev_q_end = q_start - timedelta(days=1)
    prev_q_start = date(prev_q_end.year, ((prev_q_end.month - 1) // 3) * 3 + 1, 1)
    return {
        "last7": (as_of - timedelta(days=6), as_of),
        "last15": (as_of - timedelta(days=14), as_of),
        "last30": (as_of - timedelta(days=29), as_of),
        "thisMonth": (first_this, as_of),
        "lastMonth": (last_prev.replace(day=1), last_prev),
        "lastQuarter": (prev_q_start, prev_q_end),
    }


def num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def meta_row(r: dict) -> dict:
    return {
        "d": r["date"], "p": "meta", "c": clean(r["campaign"]),
        "i": int(num(r.get("impressions"))),
        "k": int(num(r.get("link_clicks"))),
        # Leads = Meta instant-form (on-Facebook) leads only
        "l": int(num(r.get("actions_onsite_conversion_lead_grouped"))),
        "s": round(num(r.get("spend")), 2),
    }


def google_row(r: dict) -> dict:
    return {
        "d": r["date"], "p": "google", "c": clean(r["campaign"]),
        "i": int(num(r.get("impressions"))),
        "k": int(num(r.get("clicks"))),
        "l": round(num(r.get("conversions")), 2),
        "s": round(num(r.get("cost")), 2),
    }


def fx_lookup(rates: dict):
    """rates: {'YYYY-MM-DD': usd_to_ils}. Returns f(date)->rate, carrying the last known rate forward."""
    days = sorted(rates)

    def f(d: str) -> float:
        best = None
        for k in days:
            if k <= d:
                best = rates[k]
            else:
                break
        return best if best is not None else rates[days[0]]
    return f


def linkedin_row(r: dict, fx) -> dict:
    return {
        "d": r["date"], "p": "linkedin", "c": clean(r["campaign"]),
        "i": int(num(r.get("impressions"))),
        "k": int(num(r.get("clicks"))),
        # Leads = LinkedIn Lead Gen Form (one-click) leads only
        "l": int(num(r.get("oneclickleads"))),
        "s": round(num(r.get("spend")) * fx(r["date"]), 2),
    }


def campaign_status(raw: str, end, as_of: date) -> str:
    """Normalise platform status to live / paused / ended. end = 'YYYY-MM-DD...' or None."""
    raw = (raw or "").upper()
    if raw in ("COMPLETED", "REMOVED", "ARCHIVED", "DELETED", "CANCELED"):
        return "ended"
    if end and str(end)[:10] <= as_of.isoformat():
        return "ended"
    if raw in ("ACTIVE", "ENABLED"):
        return "live"
    return "paused"


def write_data(as_of: date, rows: list, reach: dict, updated_iso: str, status: dict = None) -> None:
    rows = [r for r in rows if r["i"] or r["k"] or r["l"] or r["s"]]
    rows.sort(key=lambda r: (r["d"], r["p"], r["c"]))
    pr = presets(as_of)
    out = {
        "updated": updated_iso,
        "asOf": as_of.isoformat(),
        "presets": {k: [a.isoformat(), b.isoformat()] for k, (a, b) in pr.items()},
        # reach[preset][platform] = {"total": n, "by": {campaign: n}}
        "reach": {k: {p: {"total": v["total"], "by": {clean(n): x for n, x in v.get("by", {}).items()}}
                      for p, v in plats.items()}
                  for k, plats in reach.items()},
        # status[platform][campaign] = live | paused | ended (current state, not per period)
        "status": {p: {clean(c): v for c, v in m.items()} for p, m in (status or {}).items()},
        "rows": rows,
    }
    DATA_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {DATA_FILE} rows={len(rows)} asOf={as_of}")
