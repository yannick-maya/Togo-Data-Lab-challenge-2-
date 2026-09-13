# -*- coding: utf-8 -*-
"""Join cantons RGPH-5 (pdfplumber) -> ADM3 HDX (polygones/centroïdes).

Correspondances :
  - exacte (même préfecture ADM2) puis exacte globale ;
  - aliases manuels (renommages évidents) ;
  - fuzzy (rapidfuzz, seuil 75) dans le contexte préfecture ;
  - les cantons sans polygone HDX restent 'unmatched' (population conservée,
    documentée) — aucune donnée n'est inventée.
"""
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
PDF_CSV = ROOT / "data" / "external" / "population_cantons_rgph5_2022.csv"
ADM3_CSV = Path(__file__).parent.parent / "data" / "external" / "tgo_admin3_cantons.csv"
OUT_CSV = ROOT / "data" / "external" / "canton_population_join.csv"

PREF_MAP = {                       # préfecture RGPH -> ADM2 HDX (scissions 2021)
    "Kpendjal-Ouest": "Kpendjal",
}
MANUAL = {                          # nom canton PDF (normalisé) -> nom ADM3 exact
    "KPELE-NOVIVE": "Kpele-Centre",
    "VHE": "Veh",
    "PAPRI": "Kpendjaga / Papri",
    "EKETO_GBANDI- N KOUGNA_GOBE": "Gobe/Eketo/Gbadi N'Kugna",
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = s.replace("\ufffd", "").replace("'", " ")
    out = []
    for ch in s:
        if not unicodedata.combining(ch):
            out.append(ch)
    return " ".join("".join(out).upper().split())


def main():
    pdfc = pd.read_csv(PDF_CSV)
    adm = pd.read_csv(ADM3_CSV)
    adm["n"] = adm["adm3_name"].apply(norm)
    adm["n2"] = adm["adm2_name"].apply(norm)
    by_pref = {p: g for p, g in adm.groupby("n2")}

    rows_out = []
    stats = {k: 0 for k in ("exact_pref", "exact_glob", "manual", "fuzzy", "unmatched")}
    for _, r in pdfc.iterrows():
        pref = r["prefecture"]
        context = norm(PREF_MAP.get(pref, pref))
        cname = norm(r["canton"])
        rec, method = None, None

        cand = by_pref.get(context)
        if cand is not None:
            m = cand[cand["n"] == cname]
            if len(m) == 1:
                rec, method = m.iloc[0], "exact_pref"
        if rec is None:                       # exact global
            m = adm[adm["n"] == cname]
            m = m[m["n2"] == context] if len(m) > 1 else m
            if len(m) == 1:
                rec, method = m.iloc[0], "exact_glob"
        if rec is None and cname in MANUAL:   # alias manuel
            m = adm[adm["n"] == norm(MANUAL[cname])]
            if len(m) == 1:
                rec, method = m.iloc[0], "manual"
        if rec is None and cand is not None and len(cand):   # fuzzy en contexte
            best = process.extractOne(cname, cand["n"].tolist(), scorer=fuzz.WRatio,
                                      score_cutoff=75)
            if best:
                rec, method = cand.iloc[best[2]], "fuzzy"
        if rec is None:
            method = "unmatched"

        base = {"prefecture_pdf": pref, "canton_pdf": r["canton"],
                "masculin": r["masculin"], "feminin": r["feminin"],
                "population_totale": r["population_totale"]}
        if method == "unmatched":
            base.update({"adm2_name": None, "adm3_name": None, "adm3_pcode": None,
                         "center_lat": None, "center_lon": None, "area_sqkm": None})
        else:
            base.update({"adm2_name": rec["adm2_name"], "adm3_name": rec["adm3_name"],
                         "adm3_pcode": rec["adm3_pcode"], "center_lat": rec["center_lat"],
                         "center_lon": rec["center_lon"], "area_sqkm": rec["area_sqkm"]})
        base["method"] = method
        rows_out.append(base)
        stats[method] += 1

    res = pd.DataFrame(rows_out)
    res.to_csv(OUT_CSV, index=False, encoding="utf-8")

    tot = len(res)
    done = tot - stats["unmatched"]
    print(f"Lignes : {tot} | résolues : {done} ({100*done/tot:.1f} %)")
    for k in ("exact_pref", "exact_glob", "manual", "fuzzy", "unmatched"):
        print(f"  - {k:<10}: {stats[k]}")
    if stats["unmatched"]:
        print("\nNon résolues (pas de polygone HDX) :")
        for r in res[res["method"] == "unmatched"].itertuples():
            print(f"  {r.prefecture_pdf} | {r.canton_pdf} | pop {r.population_totale}")
    # contrôle intégrité population
    joined = res[res["method"] != "unmatched"]
    assert joined["adm3_pcode"].notna().all()
    print("\nÉcrit ->", OUT_CSV)


if __name__ == "__main__":
    main()