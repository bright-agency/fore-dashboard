# FORE · Reichman University – Media Dashboard

Static dashboard (index.html + data.json) served from GitHub Pages.

- **Data:** `scripts/fetch_windsor.py` pulls Meta (692135214662669), Google Ads (521-257-8242) and LinkedIn (509671992, USD→ILS via frankfurter.dev) from the Windsor.ai API into `data.json`.
- **Schedule:** `.github/workflows/update-data.yml` runs twice a day and commits `data.json`. Needs repo secret `WINDSOR_API_KEY`.
- **Leads:** Meta = instant-form leads only (`actions_onsite_conversion_lead_grouped`); Google = conversions; LinkedIn = one-click Lead Gen Form leads.
- **Reach:** not additive across days, so it is fetched per fixed period (presets) and only shown for those.
- **Local preview:** `py -m http.server 8765` in this folder, then open http://localhost:8765.
