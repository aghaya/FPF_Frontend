"""
One-off builder for data/pipelines_live.geojson.

Pulls interstate route geometry for the live ngpipe pipelines from the public
EIA "Natural Gas Pipelines" layer (hosted by US DOT), simplified server-side,
and writes one MultiLineString feature per pipeline key.

    python scripts/build_pipeline_geojson.py

Re-run only when the pipeline registry changes. Source:
https://geo.dot.gov/server/rest/services/Hosted/Natural_Gas_Pipelines_US_EIA/FeatureServer/0
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline_registry import PIPELINES  # noqa: E402

LAYER = ("https://geo.dot.gov/server/rest/services/Hosted/"
         "Natural_Gas_Pipelines_US_EIA/FeatureServer/0/query")
OUT = ROOT / "data" / "pipelines_live.geojson"
SIMPLIFY_DEG = 0.01   # ~1 km tolerance; fine at national/regional zoom
PRECISION = 3         # decimal places (~100 m)
PAGE = 1000


def fetch_operator(op: str) -> list[list[list[float]]]:
    lines, offset = [], 0
    while True:
        params = {
            "where": f"operator = '{op}' AND typepipe = 'Interstate'",
            "outFields": "operator",
            "outSR": 4326,
            "maxAllowableOffset": SIMPLIFY_DEG,
            "geometryPrecision": PRECISION,
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "f": "geojson",
        }
        # curl rather than requests: geo.dot.gov resets TLS handshakes from
        # some Python ssl builds (seen with Python 3.15 on macOS).
        url = f"{LAYER}?{urllib.parse.urlencode(params)}"
        out = subprocess.run(["curl", "-sSf", "--max-time", "120", url],
                             check=True, capture_output=True).stdout
        feats = json.loads(out).get("features", [])
        for f in feats:
            g = f.get("geometry") or {}
            if g.get("type") == "LineString":
                lines.append(g["coordinates"])
            elif g.get("type") == "MultiLineString":
                lines.extend(g["coordinates"])
        if len(feats) < PAGE:
            break
        offset += PAGE
        time.sleep(0.5)
    # drop degenerate segments left by simplification
    return [ln for ln in lines if len(ln) >= 2]


def main() -> None:
    features = []
    for key, meta in PIPELINES.items():
        coords = []
        for op in meta["eia"]:
            coords.extend(fetch_operator(op))
            time.sleep(0.5)
        print(f"{key:10s} {len(coords):5d} segments  ({', '.join(meta['eia'])})")
        if not coords:
            continue
        features.append({
            "type": "Feature",
            "properties": {"key": key, "name": meta["name"],
                           "operator": meta["operator"],
                           "eia_operator": "; ".join(meta["eia"])},
            "geometry": {"type": "MultiLineString", "coordinates": coords},
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "type": "FeatureCollection",
        "source": LAYER.rsplit("/query", 1)[0],
        "note": f"Interstate segments only; simplified at {SIMPLIFY_DEG} deg.",
        "features": features,
    }, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(features)} pipelines)")


if __name__ == "__main__":
    main()
