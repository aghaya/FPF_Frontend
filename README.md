# FPF_Frontend

Streamlit front end for the ngpipe natural gas pipeline data (Supabase).

- `app.py`: the OAC data dashboard (Iroquois).
- `pages/1_Pipeline_Map.py`: interactive map of the live ngpipe pipelines (v1).
- `pipeline_registry.py`: pipeline keys, operator groups, EIA operator names and map colours.
- `data/pipelines_live.geojson`: static, simplified interstate route lines from the public EIA
  *Natural Gas Pipelines* layer. Rebuild with `python scripts/build_pipeline_geojson.py`.

## Run locally

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill SUPABASE_URL / SUPABASE_KEY
pip install -r requirements.txt && streamlit run app.py      # map is the "Pipeline Map" page
```

The map is token-free: pydeck with a CARTO basemap, no Mapbox account.
