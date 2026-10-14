# FORE · Reichman University – Media Dashboard

Static dashboard (index.html + data.json) served from GitHub Pages.

- **Data:** `scripts/fetch_windsor.py` pulls Meta (account 692135214662669) and Google Ads (521-257-8242) from the Windsor.ai API into `data.json`.
- **Schedule:** `.github/workflows/update-data.yml` runs twice a day and commits `data.json`. Needs repo secret `WINDSOR_API_KEY`.
- **Leads:** Meta = instant-form leads only (`actions_onsite_conversion_lead_grouped`); Google = conversions.
- **Reach:** not additive across days, so it is fetched per fixed period (presets) and only shown for those.
- **Local preview:** `py -m http.server 8765` in this folder, then open http://localhost:8765.
