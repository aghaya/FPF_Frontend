"""
FP Foundry: Pipeline Map (v1)

Interactive map of the live NG pipelines collected by ngpipe. Route lines are a
static, simplified subset of the public EIA "Natural Gas Pipelines" layer
(data/pipelines_live.geojson); daily numbers come from the <key>_oac tables in
Supabase via the same PostgREST pattern and secrets as the main dashboard.

Token-free: pydeck with a CARTO basemap (no Mapbox account needed).
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline_registry import PIPELINES, operators, table_for  # noqa: E402

st.set_page_config(
    page_title="FP Foundry | Pipeline Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEOJSON_PATH = ROOT / "data" / "pipelines_live.geojson"
NUM_COLS = ["design_capacity", "operating_capacity", "total_scheduled_quantity", "oac"]


# ---------------------------------------------------------------------------
# Supabase REST helpers (same secrets/pattern as app.py)
# ---------------------------------------------------------------------------
def _headers() -> dict:
    key = st.secrets["SUPABASE_KEY"]
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Accept":        "application/json",
    }


def _base_url(table: str) -> str:
    return f"{st.secrets['SUPABASE_URL'].rstrip('/')}/rest/v1/{table}"


def _edge_date(table: str, direction: str) -> str | None:
    r = requests.get(
        _base_url(table), headers=_headers(), timeout=30,
        params=[("select", "gas_date"), ("order", f"gas_date.{direction}"), ("limit", 1)],
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0]["gas_date"] if rows else None


@st.cache_data(ttl=3600, show_spinner=False)
def load_coverage() -> pd.DataFrame:
    """First and latest gas_date per pipeline table (2 tiny requests each)."""
    def one(key: str) -> dict:
        t = table_for(key)
        return {"key": key, "first": _edge_date(t, "asc"), "latest": _edge_date(t, "desc")}
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(one, PIPELINES))
    return pd.DataFrame(rows).set_index("key")


def _fetch_day(key: str, gas_date: date) -> pd.DataFrame:
    """All rows for one pipeline and gas day, only the columns we aggregate."""
    rows, offset, page = [], 0, 1000
    while True:
        r = requests.get(
            _base_url(table_for(key)), headers=_headers(), timeout=30,
            params=[("select", "loc," + ",".join(NUM_COLS)),
                    ("gas_date", f"eq.{gas_date}"),
                    ("order", "loc"),
                    ("offset", offset), ("limit", page)],
        )
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return pd.DataFrame(rows, columns=["loc", *NUM_COLS])


@st.cache_data(ttl=900, show_spinner=False)
def load_day_summary(keys: tuple[str, ...], gas_date: date) -> pd.DataFrame:
    """One row per pipeline: location count and summed quantities for the day."""
    def summarise(key: str) -> dict:
        df = _fetch_day(key, gas_date)
        for c in NUM_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        both = df.dropna(subset=["operating_capacity", "total_scheduled_quantity"])
        both = both[both["operating_capacity"] > 0]
        util = (both["total_scheduled_quantity"].sum() / both["operating_capacity"].sum()
                if not both.empty else None)
        return {
            "key": key,
            "rows": len(df),
            "locations": df["loc"].nunique(),
            "scheduled": df["total_scheduled_quantity"].sum(min_count=1),
            "operating_capacity": df["operating_capacity"].sum(min_count=1),
            "design_capacity": df["design_capacity"].sum(min_count=1),
            "oac": df["oac"].sum(min_count=1),
            "utilisation": util,
        }
    if not keys:
        return pd.DataFrame()
    with ThreadPoolExecutor(max_workers=6) as ex:
        out = list(ex.map(summarise, keys))
    return pd.DataFrame(out).set_index("key")


@st.cache_data(show_spinner=False)
def load_routes() -> dict:
    return json.loads(GEOJSON_PATH.read_text())


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def fmt_qty(x, unit: str = " MMBtu") -> str:
    if x is None or pd.isna(x):
        return "n/a"
    x = float(x)
    if abs(x) >= 1e6:
        return f"{x / 1e6:,.2f}M{unit}"
    return f"{x:,.0f}{unit}"


def fmt_pct(x) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{100 * float(x):.1f}%"


def rgb_hex(c: list[int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*c)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.spinner("Checking data coverage..."):
    coverage = load_coverage()

latest_overall = pd.to_datetime(coverage["latest"].dropna()).max().date()
first_overall = pd.to_datetime(coverage["first"].dropna()).min().date()

with st.sidebar:
    st.title("Pipeline Map")
    st.caption("Live ngpipe pipelines · v1 for review")
    st.divider()

    gas_date = st.date_input(
        "Gas day",
        value=latest_overall,
        min_value=first_overall,
        max_value=latest_overall,
        help="Defaults to the latest gas day in Supabase.",
    )

    st.subheader("Pipelines")
    selected: list[str] = []
    for op, keys in operators().items():
        with st.expander(f"{op} ({len(keys)})", expanded=len(keys) > 1):
            all_key = f"all_{op}"
            if all_key not in st.session_state:
                st.session_state[all_key] = True

            def _toggle_all(op=op, keys=keys):
                for k in keys:
                    st.session_state[f"pl_{k}"] = st.session_state[f"all_{op}"]

            st.checkbox("Select all", key=all_key, on_change=_toggle_all)
            for k in keys:
                if f"pl_{k}" not in st.session_state:
                    st.session_state[f"pl_{k}"] = True
                if st.checkbox(PIPELINES[k]["name"], key=f"pl_{k}"):
                    selected.append(k)

    st.divider()
    st.caption(
        "Routes: EIA *Natural Gas Pipelines* (interstate segments, simplified).  \n"
        "Numbers: operator EBB OAC postings via ngpipe → Supabase.  \n"
        f"Latest gas day in DB: **{latest_overall}**"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("Natural Gas Pipelines: Daily Capacity Map")
st.caption(f"Gas day **{gas_date:%b %d, %Y}** · {len(selected)} of {len(PIPELINES)} pipelines shown")

if not selected:
    st.info("Select at least one pipeline in the sidebar.")
    st.stop()

with st.spinner("Loading daily totals..."):
    summary = load_day_summary(tuple(selected), gas_date)

routes = load_routes()

# Flatten routes to one record per path so tooltips can use flat fields.
paths = []
for feat in routes["features"]:
    key = feat["properties"]["key"]
    if key not in selected:
        continue
    meta = PIPELINES[key]
    s = summary.loc[key] if key in summary.index else None
    has = s is not None and s["rows"] > 0
    info = {
        "key": key,
        "name": meta["name"],
        "operator": meta["operator"],
        "color": meta["color"],
        "locs": f"{int(s['locations']):,}" if has else "no data",
        "sched": fmt_qty(s["scheduled"]) if has else "n/a",
        "opcap": fmt_qty(s["operating_capacity"]) if has else "n/a",
        "util": fmt_pct(s["utilisation"]) if has else "n/a",
        "oac": fmt_qty(s["oac"]) if has else "n/a",
    }
    for line in feat["geometry"]["coordinates"]:
        paths.append({**info, "path": line})

layer = pdk.Layer(
    "PathLayer",
    id="routes",
    data=paths,
    get_path="path",
    get_color="color",
    # NB: pydeck turns string props such as width_units="pixels" into JS
    # accessors, which breaks widths; clamp metre widths to pixels instead.
    get_width=50,
    width_min_pixels=2,
    width_max_pixels=3,
    joint_rounded=True,
    cap_rounded=True,
    pickable=True,
    auto_highlight=True,
    highlight_color=[255, 255, 255, 200],
)

tooltip = {
    "html": (
        "<b>{name}</b> <span style='opacity:.7'>({operator})</span><br/>"
        f"Gas day {gas_date}<br/>"
        "Locations: {locs}<br/>"
        "Scheduled: {sched}<br/>"
        "Operating cap: {opcap}<br/>"
        "Utilisation: {util}<br/>"
        "OAC: {oac}"
    ),
    "style": {"backgroundColor": "#0f172a", "color": "#e2e8f0",
              "fontSize": "12px", "padding": "8px 10px", "borderRadius": "6px"},
}

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=pdk.ViewState(latitude=38.5, longitude=-96.0, zoom=3.6),
    map_provider="carto",
    map_style="dark",
    tooltip=tooltip,
)

event = st.pydeck_chart(
    deck, width="stretch", height=600,
    on_select="rerun", selection_mode="single-object", key="map",
)

# Colour legend
st.markdown(
    " ".join(
        f"<span style='white-space:nowrap;margin-right:14px;font-size:13px'>"
        f"<span style='display:inline-block;width:18px;height:4px;border-radius:2px;"
        f"vertical-align:middle;background:{rgb_hex(PIPELINES[k]['color'])}'></span> "
        f"{PIPELINES[k]['name']}</span>"
        for k in selected
    ),
    unsafe_allow_html=True,
)

# Click a route -> detail card
clicked = None
try:
    objs = event.selection["objects"].get("routes", [])
    if objs:
        clicked = objs[0]["key"]
except (AttributeError, KeyError, TypeError):
    clicked = None

if clicked and clicked in summary.index:
    s = summary.loc[clicked]
    meta = PIPELINES[clicked]
    st.subheader(f"{meta['name']} · {gas_date:%b %d, %Y}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Locations", f"{int(s['locations']):,}")
    c2.metric("Scheduled (MMBtu)", fmt_qty(s["scheduled"], ""))
    c3.metric("Operating cap (MMBtu)", fmt_qty(s["operating_capacity"], ""))
    c4.metric("Utilisation", fmt_pct(s["utilisation"]))
    c5.metric("OAC (MMBtu)", fmt_qty(s["oac"], ""))
else:
    st.caption("Hover a route for its daily summary; click one to pin it here.")

# Summary table for everything shown
st.subheader("Selected pipelines")
tbl = pd.DataFrame([
    {
        "Pipeline": PIPELINES[k]["name"],
        "Operator": PIPELINES[k]["operator"],
        "Locations": int(summary.loc[k, "locations"]),
        "Scheduled (MMBtu)": summary.loc[k, "scheduled"],
        "Operating cap (MMBtu)": summary.loc[k, "operating_capacity"],
        "Utilisation": summary.loc[k, "utilisation"],
        "OAC (MMBtu)": summary.loc[k, "oac"],
        "Data through": coverage.loc[k, "latest"],
    }
    for k in selected if k in summary.index
])
st.dataframe(
    tbl,
    hide_index=True,
    width="stretch",
    column_config={
        "Scheduled (MMBtu)": st.column_config.NumberColumn(format="%,.0f"),
        "Operating cap (MMBtu)": st.column_config.NumberColumn(format="%,.0f"),
        "OAC (MMBtu)": st.column_config.NumberColumn(format="%,.0f"),
        "Utilisation": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
    },
)

missing = [PIPELINES[k]["name"] for k in selected if k in summary.index and summary.loc[k, "rows"] == 0]
if missing:
    st.warning(f"No rows for {gas_date} on: {', '.join(missing)}.")

st.caption(
    "Totals are sums across every posted location (receipt, delivery, segment and "
    "storage points) for the gas day, so they are not pipeline throughput. "
    "Utilisation = scheduled ÷ operating capacity over points reporting both. "
    "Route geometry: US EIA via geo.dot.gov; basemap © CARTO, © OpenStreetMap contributors."
)
