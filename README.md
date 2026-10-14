# FORE · Reichman University – Media Dashboard

Static dashboard (index.html + data.json) served from GitHub Pages.

- **Data:** `scripts/fetch_windsor.py` pulls Meta (692135214662669), Google Ads (521-257-8242) and LinkedIn (509671992, USD→ILS via frankfurter.dev) from the Windsor.ai API into `data.json`.
- **Schedule:** `.github/workflows/update-data.yml` runs twice a day and commits `data.json`. Needs repo secret `WINDSOR_API_KEY`.
- **Leads:** Meta = instant-form leads only (`actions_onsite_conversion_lead_grouped`); Google = conversions; LinkedIn = one-click Lead Gen Form leads.
- **Reach:** not additive across days, so it is fetched per fixed period (presets) and only shown for those.
- **Local preview:** `py -m http.server 8765` in this folder, then open http://localhost:8765.
- **Team dashboard:** `team/` (password page, BRIGHT internal). Built by `scripts/fetch_internal.py` + `scripts/internal.py` into `team/data.enc.json` (AES-GCM, secret `INTERNAL_PASSWORD`). Course grouping, budget pacing, alerts, ad/ad-set drill-down, breakdowns. Data schema for agents: `team/AGENT.md`. Local preview uses `team/internal.dev.json` (git-ignored, build with `scripts/seed_internal.py`).
- **New client:** edit `scripts/client.json`.
