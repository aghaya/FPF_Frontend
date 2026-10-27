"""
Registry of the live NG pipelines shown on the map.

Each entry maps an ngpipe key (Supabase table ``<key>_oac``) to a display name,
the operator group used in the sidebar, the operator name(s) used in the EIA
"Natural Gas Pipelines" layer (for route geometry), and a map colour.

Operator groups follow the EBB / operating company that posts the data.
"""

from __future__ import annotations

PIPELINES: dict[str, dict] = {
    # Kinder Morgan
    "tgp":      {"name": "Tennessee Gas Pipeline",          "operator": "Kinder Morgan",   "eia": ["Tennessee Gas Pipeline"],           "color": [31, 119, 180]},
    "ngpl":     {"name": "Natural Gas Pipeline Co. of America", "operator": "Kinder Morgan", "eia": ["Natural Gas PL Co of Am"],        "color": [23, 190, 207]},
    "epng":     {"name": "El Paso Natural Gas",             "operator": "Kinder Morgan",   "eia": ["El Paso Natural Gas Co"],           "color": [255, 127, 14]},
    "sng":      {"name": "Southern Natural Gas",            "operator": "Kinder Morgan",   "eia": ["Southern Natural Gas Co"],          "color": [148, 103, 189]},
    "cig":      {"name": "Colorado Interstate Gas",         "operator": "Kinder Morgan",   "eia": ["Colorado Interstate Gas Co"],       "color": [140, 86, 75]},
    "wic":      {"name": "Wyoming Interstate",              "operator": "Kinder Morgan",   "eia": ["Wyoming Interstate PL Co"],         "color": [188, 189, 34]},
    "cheyenne": {"name": "Cheyenne Plains",                 "operator": "Kinder Morgan",   "eia": ["Cheyenne Plains Pipeline Co"],      "color": [227, 119, 194]},
    "elba":     {"name": "Elba Express",                    "operator": "Kinder Morgan",   "eia": ["Elba Express Pipeline"],            "color": [127, 127, 127]},
    # Williams
    "transco":  {"name": "Transco",                         "operator": "Williams",        "eia": ["Transcontinental Gas PL"],          "color": [214, 39, 40]},
    "nwp":      {"name": "Northwest Pipeline",              "operator": "Williams",        "eia": ["Northwest Pipeline"],               "color": [255, 152, 150]},
    # Enbridge
    "tetco":    {"name": "Texas Eastern",                   "operator": "Enbridge",        "eia": ["Texas Eastern Trans Co"],           "color": [44, 160, 44]},
    "agt":      {"name": "Algonquin Gas Transmission",      "operator": "Enbridge",        "eia": ["Algonquin Gas Trans Co"],           "color": [152, 223, 138]},
    # TC Energy
    "anr":      {"name": "ANR Pipeline",                    "operator": "TC Energy",       "eia": ["ANR Pipeline Co"],                  "color": [174, 199, 232]},
    # Energy Transfer
    "pepl":     {"name": "Panhandle Eastern",               "operator": "Energy Transfer", "eia": ["Panhandle Eastern PL Co"],          "color": [197, 176, 213]},
    "rover":    {"name": "Rover Pipeline",                  "operator": "Energy Transfer", "eia": ["Rover Pipeline"],                   "color": [255, 187, 120]},
    # Tallgrass
    "rex":      {"name": "Rockies Express",                 "operator": "Tallgrass",       "eia": ["Rockies Express Pipeline", "Rockies Express (Entrega)", "Rockies Express (Echo Springs Lateral)"], "color": [219, 219, 141]},
    # Single-pipeline operators
    "nng":      {"name": "Northern Natural Gas",            "operator": "Northern Natural (BHE)", "eia": ["Northern Natural Gas Co"],    "color": [158, 218, 229]},
    "nfg":      {"name": "National Fuel Gas Supply",        "operator": "National Fuel",   "eia": ["National Fuel Gas Supply Co"],      "color": [196, 156, 148]},
    "iroquois": {"name": "Iroquois Gas Transmission",       "operator": "Iroquois",        "eia": ["Iroquois Gas Trans Co"],            "color": [247, 182, 210]},
}


def table_for(key: str) -> str:
    return f"{key}_oac"


def operators() -> dict[str, list[str]]:
    """Operator group -> pipeline keys, in registry order."""
    out: dict[str, list[str]] = {}
    for key, meta in PIPELINES.items():
        out.setdefault(meta["operator"], []).append(key)
    return out
