# Team dashboard data: guide for an AI agent

The campaigners dashboard (`team/index.html`) and any future client agent read the same payload.

## Where the data is
- `team/data.enc.json` is encrypted with the INTERNAL_PASSWORD secret: gzip, then AES-256-GCM, with the key from PBKDF2-SHA256.
  - Fields: `{v, kdf, iter, salt, iv, gzip, ct}`, all base64.
  - To decrypt in Python: `PBKDF2HMAC(SHA256, 32, salt, iter).derive(pw)`, then `AESGCM(key).decrypt(iv, ct, None)`, then `gzip.decompress`, then `json.loads`.
- An agent running inside the workflow can call `internal.build()` directly (`scripts/fetch_internal.py`) and skip decryption.
- It's refreshed twice a day by `.github/workflows/update-data.yml`.

## Payload (schema 1)
| key | content |
|---|---|
| `meta` | `client, generated, asOf` (last full day), `currency` (always ILS), `detailFrom` (start of the ad and breakdown data), `presets` |
| `days` | list of dates. Every `d` in the rows is an index into this list |
| `courses[]` | `key, name, start` (course opening date), `launch, phase` (live/paused/ended), `daysLeft, live` (number of live campaigns), `campaigns` (indexes), `budget` (sum of the budgets in the campaign names), `budgetSpent, spent, leads, cpl, avg7, budgetAvg7, expected, pace` (budgetSpent/expected), `elapsedPct, remaining, requiredDaily, projected, dailySet, budgetMissing`, `brand` (true = the "brand and general" group) |
| `campaigns[]` | `p` (meta/google/linkedin), `name, course` (index), `type, status` (live/paused/ended), `budget` (from the name), `daily` (the daily budget set on the platform, ILS), `start, end, launch` |
| `rows` | `[d, campaign, impressions, clicks, leads, spend]`, daily per campaign, from history_start |
| `units[]` | `p, c` (campaign), `set` (ad set / ad group / LinkedIn campaign), `ad, id, thumb, setStatus` |
| `unitRows` | `[d, unit, impressions, clicks, leads, spend]`, from detailFrom |
| `dims` / `breakdowns` | `meta_place, meta_device, meta_age, meta_gender, google_device`. Each row is `[d, campaign, dimIndex, i, k, l, s]` |
| `liDemo` | `{preset: {func:[[name,i,k,l,s]], senior:[...]}}`. LinkedIn at the whole-account level |
| `reach` | Reach per preset period, per platform and per campaign |
| `alerts[]` | `sev` (high/med/info), `type, msg` (Hebrew), `p, campaign, course, value` |

## Definitions
- Leads: Meta counts instant-form leads only (`actions_onsite_conversion_lead_grouped`). LinkedIn counts Lead Gen Form leads (`oneclickleads`). Google counts conversions.
- LinkedIn spend comes in USD and is converted to ILS at the daily ECB rate.
- Clicks: Meta counts link clicks.
- Alert types: `no_spend, no_leads, cpl_up, frequency, under_pace, over_pace, projected_over, course_soon, live_after_start`. Thresholds are in `scripts/client.json` → `alerts`.

## New client
Copy the repo and edit `scripts/client.json` (accounts, logo, thresholds). Then set the secrets `WINDSOR_API_KEY` and `INTERNAL_PASSWORD`.
