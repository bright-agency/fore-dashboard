"""Builds the internal campaigners dashboard data (team/data.enc.json).

Runs after fetch_windsor.py (needs the fresh data.json). Env:
  WINDSOR_API_KEY     - Windsor.ai key
  INTERNAL_PASSWORD   - password for the team page; the payload is gzip + AES-256-GCM encrypted with it
  INTERNAL_PLAIN=1    - (local only) also write team/internal.dev.json in plain text - never commit it
"""
import base64
import gzip
import json
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from common import CONFIG, DATA_FILE, GOOGLE_ACCOUNT, HISTORY_START, LINKEDIN_ACCOUNT, META_ACCOUNT, ROOT  # noqa: E402
import internal  # noqa: E402

M = ["impressions", "link_clicks", "spend", "actions_onsite_conversion_lead_grouped"]
G = ["impressions", "clicks", "cost", "conversions"]
L = ["impressions", "clicks", "spend", "oneclickleads"]
# name -> (connector, account, fields, period) ; period: "detail" = last detail_days, "history" = HISTORY_START..as_of
DATASETS = {
    "meta_ads":     ("facebook", META_ACCOUNT, ["date", "campaign", "adset_name", "ad_id", "ad_name"] + M, "detail"),
    "meta_ad_info": ("facebook", META_ACCOUNT, ["ad_id", "ad_name", "adset_name", "adset_id", "campaign", "campaign_id",
                                                "thumbnail_url", "adset_effective_status", "ad_preview_shareable_link"], "detail"),
    "meta_place":   ("facebook", META_ACCOUNT, ["date", "campaign", "publisher_platform", "platform_position"] + M, "detail"),
    "meta_device":  ("facebook", META_ACCOUNT, ["date", "campaign", "device_platform"] + M, "detail"),
    "meta_demo":    ("facebook", META_ACCOUNT, ["date", "campaign", "age", "gender"] + M, "detail"),
    "meta_camp":    ("facebook", META_ACCOUNT, ["campaign", "campaign_id", "campaign_lifetime_budget", "campaign_daily_budget",
                                                "campaign_start_time", "campaign_stop_time", "campaign_effective_status"], "history"),
    "g_adgroup":    ("google_ads", GOOGLE_ACCOUNT, ["date", "campaign", "ad_group_name", "ad_group_status"] + G, "detail"),
    "g_adgroup_info": ("google_ads", GOOGLE_ACCOUNT, ["campaign", "campaign_id", "ad_group_name", "ad_group_id"], "detail"),
    "g_device":     ("google_ads", GOOGLE_ACCOUNT, ["date", "campaign", "device"] + G, "detail"),
    "li_creative":  ("linkedin", LINKEDIN_ACCOUNT, ["date", "campaign", "creative_id", "sponsored_creative_content_title",
                                                    "creative_content_data_share_ad_context_dsc_name"] + L, "detail"),
    "li_creative_info": ("linkedin", LINKEDIN_ACCOUNT, ["creative_id", "campaign", "campaign_id", "ad_post_url"], "detail"),
    "li_camp":      ("linkedin", LINKEDIN_ACCOUNT, ["campaign", "campaign_id", "campaign_group_name", "campaign_start_date", "campaign_end_date",
                                                    "campaign_total_budget_amount", "campaign_daily_budget_amount",
                                                    "campaign_status"], "history"),
}


def encrypt(payload: dict, password: str) -> dict:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt, iv, iters = os.urandom(16), os.urandom(12), 310_000
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iters).derive(password.encode())
    data = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    ct = AESGCM(key).encrypt(iv, data, None)
    b = lambda x: base64.b64encode(x).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": iters, "salt": b(salt), "iv": b(iv), "gzip": True, "ct": b(ct)}


def decrypt(enc: dict, password: str):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    d = lambda x: base64.b64decode(x)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=d(enc["salt"]), iterations=enc["iter"]).derive(password.encode())
    data = AESGCM(key).decrypt(d(enc["iv"]), d(enc["ct"]), None)
    return json.loads(gzip.decompress(data) if enc.get("gzip") else data)


def load_budgets() -> dict:
    """Manual course budgets saved from the team page (team/budgets.enc.json, same encryption)."""
    path, pw = ROOT / "team" / "budgets.enc.json", os.environ.get("INTERNAL_PASSWORD", "").strip()
    if not path.exists() or not pw:
        return {}
    try:
        return decrypt(json.loads(path.read_text(encoding="utf-8")), pw).get("courses", {})
    except Exception as e:  # wrong password / corrupt file must not break the refresh
        print("could not read budgets.enc.json:", e)
        return {}


def write_config() -> dict:
    """Lets the team page save budgets: a fine-grained token (contents:write on this repo only), shipped encrypted."""
    tok = os.environ.get("TEAM_WRITE_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not tok or not repo:
        return None
    return {"repo": repo, "path": "team/budgets.enc.json", "branch": "main", "token": tok}


def write_outputs(payload: dict) -> None:
    team = ROOT / "team"
    pw = os.environ.get("INTERNAL_PASSWORD", "").strip()
    if pw:
        (team / "data.enc.json").write_text(json.dumps(encrypt(payload, pw)), encoding="utf-8")
        print("wrote team/data.enc.json")
    else:
        print("INTERNAL_PASSWORD not set - encrypted file not written")
    if os.environ.get("INTERNAL_PLAIN") == "1":
        (team / "internal.dev.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                                                encoding="utf-8")
        print("wrote team/internal.dev.json (local, git-ignored)")


def main():
    from fetch_windsor import KEY, get, usd_ils
    if not KEY:
        sys.exit("WINDSOR_API_KEY is not set")
    if not os.environ.get("INTERNAL_PASSWORD", "").strip() and os.environ.get("INTERNAL_PLAIN") != "1":
        print("INTERNAL_PASSWORD not set - skipping team dashboard build")
        return
    client = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    as_of = date.fromisoformat(client["asOf"])
    detail_from = as_of - timedelta(days=CONFIG.get("detail_days", 120) - 1)
    raw = {}
    for name, (conn, acc, fields, period) in DATASETS.items():
        raw[name] = get(conn, acc, fields, detail_from if period == "detail" else HISTORY_START, as_of)
        print(f"{name}: {len(raw[name])} rows")
    raw["li_demo"] = {}
    for key, (a, b) in client["presets"].items():
        a, b = date.fromisoformat(a), date.fromisoformat(b)
        raw["li_demo"][key] = {
            "func": get("linkedin", LINKEDIN_ACCOUNT, ["member_job_function"] + L, a, b),
            "senior": get("linkedin", LINKEDIN_ACCOUNT, ["member_seniority"] + L, a, b)}
    fx = usd_ils(HISTORY_START, as_of)
    now = datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(timespec="minutes")
    budgets = load_budgets()
    print("manual budgets:", len(budgets))
    payload = internal.build(client, raw, fx, now, budgets)
    payload["meta"]["write"] = write_config()
    print("budget editing:", "enabled" if payload["meta"]["write"] else "disabled (no TEAM_WRITE_TOKEN)")
    from collections import Counter
    print("unit links:", dict(Counter((u["p"], ",".join(sorted(u["links"]))) for u in payload["units"])))
    print("campaign links:", sum(1 for c in payload["campaigns"] if c["url"]), "/", len(payload["campaigns"]))
    write_outputs(payload)


if __name__ == "__main__":
    main()
