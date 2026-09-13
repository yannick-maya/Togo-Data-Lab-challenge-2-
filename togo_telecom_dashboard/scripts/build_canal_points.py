# -*- coding: utf-8 -*-
"""CANAL+ points de vente : fusion canalbox (API officielle) + OSM (Overpass),
avec filtre des entrées non pertinentes (cinémas, homonymes)."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "external" / "canal_points.csv"


def main():
    rec = []
    # API canalbox.tg
    with open(ROOT / "data" / "external" / "canalbox_stores_2026.json", encoding="utf-8") as f:
        stores = json.load(f)
    for s in stores:
        rec.append({"name": s["name"].strip(), "commune": ("Golfe" if s["name"].strip() == "AGOE" else "Golfe"),
                    "lat": float(s["coordinates_latitude"]), "lon": float(s["coordinates_longitude"]),
                    "type": s["type"], "source": "canalbox"})

    # OSM : ne garder que les points de vente / distributeurs (exclure cinémas, homonymes)
    with open(ROOT / "data" / "external" / "canal_osm_points_2026.json", encoding="utf-8") as f:
        osm = json.load(f)
    keep_kw = ("store", "distributeur", "boutique", "agence canal", "horizon")
    for e in osm["elements"]:
        tags = e.get("tags", {})
        name = tags.get("name", "").lower()
        if "cinema" in str(tags.get("amenity", "")).lower():
            continue
        plus = "canal" in name and ("+" in name or " plus" in name or "store" in name)
        if plus or any(k in name for k in keep_kw):
            if any(x in name for x in ("saveur", "hotel", "hôtel", "restau")):
                continue
            rec.append({"name": tags.get("name", "?"), "commune": tags.get("addr:municipality", ""),
                        "lat": e["lat"], "lon": e["lon"], "type": "OSM",
                        "source": "osm"})

    df = pd.DataFrame(rec).drop_duplicates(["lat", "lon"])
    # exclusion homonymes évidents restants (ex. Canal wak → gardés ? non)
    df = df[~df["name"].str.lower().str.startswith("canal wak")]
    df.to_csv(OUT, index=False, encoding="utf-8")
    print("points CANAL+:", len(df))
    print(df[["name", "commune", "lat", "lon", "source"]].to_string())


if __name__ == "__main__":
    main()