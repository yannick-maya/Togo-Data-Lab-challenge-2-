# -*- coding: utf-8 -*-
"""Extract canton population from INSEED RGPH-5 Livret 01 (block-based, validated).

Source : INSEED Togo, RGPH-5 (nov. 2022), Livret 01 « Distribution spatiale de la
population résidente par sexe ».
Structure : pour chaque préfecture, un tableau « canton » lignes [COMMUNE DE ... n
(subtotal) + ligne(s) canton + ... + TOTAL PREFECTURE DE X]. Grand Lomé (Golfe,
Agoè-Nyivé) est publié par quartier (pas de tableau canton) ; Danyi n'a pas de
canton (2 communes). Les tableaux finaux (population communale / récapitulatifs
régionaux) sont écartés.

Chaque bloc est identifié par son total (ligne « TOTAL PREFECTURE ») mis en
correspondance EXACT avec population_prefectures_togo_2022.csv ; les sous-totaux
de commune sont détectés par « somme des lignes suivantes == sous-total ».
"""
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
PDF = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "rgph5_livret01.pdf"
POP_CSV = ROOT / "data" / "external" / "population_prefectures_togo_2022.csv"
OUT_CSV = ROOT / "data" / "external" / "population_cantons_rgph5_2022.csv"

NO_CANTON_TABLE = ["Golfe", "Agoè-Nyivé", "Danyi"]  # quartiers ou communes seules


def to_int(v):
    if v is None:
        return None
    s = str(v).replace("\u00a0", " ").replace(" ", "").strip()
    return int(s) if s.isdigit() else None


def split_groups(rows):
    """Découpe la liste de lignes en (sous_total_ou_None, [enfants_canton])."""
    groups, i, n = [], 0, len(rows)
    while i < n:
        name, ens = rows[i]
        acc, j, start = 0, i + 1, i
        while j < n and acc < ens:
            acc += rows[j][1]
            j += 1
        if acc == ens and j > i + 1:
            groups.append((name, rows[i + 1:j]))
            i = j
        else:
            groups.append((None, [rows[i]]))
            i += 1
    return groups


def expand_rows(cells):
    """Si une cellule de valeur contient des retours ligne (sous-total+canton
    fusionnés), renvoie les deux lignes séparées ; sinon [ligne unique]."""
    parts = [c.split("\n") for c in cells]
    multi_value = any(len(p) > 1 for p in parts[1:])
    if multi_value:
        if all(len(p) == 2 for p in parts):
            return [[p[0].strip() for p in parts], [p[1].strip() for p in parts]]
        return None  # cas ambigu : on écarte la ligne
    name = " ".join(p.strip() for p in parts[0]) if len(parts[0]) > 1 else parts[0][0].strip()
    return [[name] + [p[0].strip() for p in parts[1:]]]


def main():
    pdf = pdfplumber.open(str(PDF))
    blocks = []  # (rows, total: int or None)
    cur, cur_total = [], None
    for pageno in range(51, len(pdf.pages)):
        tbl = pdf.pages[pageno].extract_table()
        if not tbl:
            continue
        for row in tbl:
            cells = [c.strip() if c else "" for c in (row or []) if c]
            clones = expand_rows(cells)
            if clones is None:
                continue
            for clone in clones:
                clone = [c.strip() for c in clone if c is not None]
                if not clone:
                    continue
                name = clone[0]
                if not name or name.startswith(("Tableau", "Sexe", "Distribution", "Commune / Canton")):
                    continue
                vals = [to_int(c) for c in clone[1:]]
                vals = [v for v in vals if v is not None][-3:]
                if len(vals) < 3:
                    continue
                rec = {"nom": name, "masculin": vals[-3], "feminin": vals[-2], "ensemble": vals[-1],
                       "is_total": "TOTAL" in name.upper(), "page": pageno}
                if rec["is_total"]:
                    blocks.append((cur, rec["ensemble"]))
                    cur, cur_total = [], None
                else:
                    cur.append(rec)
    if cur:
        blocks.append((cur, cur_total))
    pdf.close()

    pop = pd.read_csv(POP_CSV)
    pop_indexed = pop.set_index("prefecture")
    canton_rows = []
    resolved, dropped = [], []
    for bi, (rows, total) in enumerate(blocks):
        hits = pop[pop["population_totale"] == total] if total is not None else pop.iloc[0:0]
        if len(hits) != 1:
            dropped.append((bi, total))
            continue
        pref = hits.iloc[0]["prefecture"]
        groups = split_groups([(r["nom"], r["ensemble"]) for r in rows])
        children_filtered = [
            name for _, kids in groups for (name, _) in kids
            if not name.upper().startswith("COMMUNE")
        ]
        # reconstruction : il faut le détail m/f -> relie par nom
        lookup = {r["nom"]: r for r in rows}
        for name in children_filtered:
            rec = lookup[name]
            canton_rows.append({"prefecture": pref, "canton": name,
                                "masculin": rec["masculin"], "feminin": rec["feminin"],
                                "population_totale": rec["ensemble"],
                                "source_page": rec["page"] + 1})
        resolved.append((pref, total))

    df = pd.DataFrame(canton_rows)
    # ---- validations ----
    covered = {p for p, _ in resolved}
    missing = set(pop["prefecture"]) - covered - set(NO_CANTON_TABLE)
    assert not missing, f"préfectures non couvertes : {missing}"
    for pref, tot in resolved:
        s = int(df[df["prefecture"] == pref]["population_totale"].sum())
        csvv = int(pop_indexed.loc[pref, "population_totale"])
        assert s == tot == csvv, f"{pref}: canton {s} != total {tot} != csv {csvv}"
    attendu = int(pop["population_totale"].sum()
                  - pop_indexed.loc[["Golfe", "Agoè-Nyivé", "Danyi"], "population_totale"].sum())
    assert int(df["population_totale"].sum()) == attendu, "validation somme nationale KO"
    print(f"Blocs résolus : {len(resolved)} ; blocs écartés (récapitulatifs) : {len(dropped)}")
    print(f"Préfectures couvertes : {len(covered)} ; lignes canton : {len(df)}")
    print(f"Somme totale : {attendu:,} (hors Grand Lomé et Danyi)".replace(",", " "))
    print("Validation somme nationale : OK")
    print("Écrit ->", OUT_CSV)
    df = df.drop(columns=["source_page"])
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()