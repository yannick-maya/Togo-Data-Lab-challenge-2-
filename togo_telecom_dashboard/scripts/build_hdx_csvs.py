# -*- coding: utf-8 -*-
"""Flat CSV from HDX COD-AB Togo geojsons (ADM2 + ADM3 centroids)."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "external" / "tgo_admin_boundaries.geojson.zip"
OUT2 = ROOT / "data" / "external" / "tgo_admin2_prefectures.csv"
OUT3 = ROOT / "data" / "external" / "tgo_admin3_cantons.csv"
EXTRACT = Path(__file__).parent / "_hdx_extract"


def unzip_feature(name):
    out = EXTRACT / name
    import zipfile
    with zipfile.ZipFile(SRC) as z:
        z.extract(name, EXTRACT)
    return out


def geojson_to_df(path, props):
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    rows = []
    for feat in gj["features"]:
        p = feat["properties"]
        rows.append({k: p.get(k) for k in props})
    return pd.DataFrame(rows)


def main():
    a2 = unzip_feature("tgo_admin2.geojson")
    a3 = unzip_feature("tgo_admin3.geojson")
    adm2 = geojson_to_df(a2, ["adm2_pcode", "adm2_name", "center_lat", "center_lon", "area_sqkm"])
    adm3 = geojson_to_df(a3, ["adm2_pcode", "adm2_name", "adm3_pcode", "adm3_name",
                              "center_lat", "center_lon", "area_sqkm"])
    print("ADM2:", len(adm2), "| ADM3:", len(adm3))
    assert len(adm2) == 40 and len(adm3) == 373
    adm2.to_csv(OUT2, index=False, encoding="utf-8")
    adm3.to_csv(OUT3, index=False, encoding="utf-8")
    print("Écrit ->", OUT2, "/", OUT3)


if __name__ == "__main__":
    main()