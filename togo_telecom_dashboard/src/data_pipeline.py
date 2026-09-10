"""
Pipeline de préparation des données — Challenge Télécoms & Inclusion Numérique (Togo)

Ce script lit les fichiers bruts (data/raw/) et les données externes
(data/external/), puis produit les fichiers nettoyés et les indicateurs
utilisés par l'application Streamlit dans data/processed/.

Lancer depuis la racine du projet :
    python src/data_pipeline.py

Choix méthodologiques (voir aussi data/external/README_donnees_externes.md) :
  - Le fichier "Agences - Télécom" est écarté car il correspond exactement
    à la réunion de "Agences - Togocom" + "Agences - Moov" (91 = 62 + 29
    lignes) : le garder en plus aurait doublé le comptage des agences.
  - "Agences - CANAL+" est vide dans le jeu de données fourni : il est
    chargé mais signalé comme tel plutôt qu'ignoré silencieusement.
  - La population est disponible officiellement au niveau PRÉFECTURE
    (RGPH-5, INSEED 2022) mais pas au niveau CANTON dans les données
    rapidement mobilisables pour ce challenge. Les indicateurs "par
    habitant" sont donc calculés au niveau préfecture ; au niveau canton,
    la notion de "zone blanche" repose uniquement sur la présence/absence
    d'un point de service (proxy infrastructure, sans pondération
    démographique). Ce choix est assumé et documenté dans le rapport.
"""
from pathlib import Path
import json
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import add_lonlat, polygon_key, shape_group_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
EXTERNAL = ROOT / "data" / "external"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

ADMIN_COLS = [
    "region_nom_bdd",
    "prefecture_nom_bdd",
    "commune_nom_bdd",
    "canton_nom_bdd",
]


def log(msg: str):
    print(f"[pipeline] {msg}")


def load_agences() -> pd.DataFrame:
    """Unifie les agences Togocom + Moov (le fichier 'Télécom' est un doublon, voir docstring)."""
    togocom = pd.read_csv(RAW / "agences_togocom.csv")
    moov = pd.read_csv(RAW / "agences_moov.csv")

    togocom["operateur"] = "Togocom"
    moov["operateur"] = "Moov"

    agences = pd.concat([togocom, moov], ignore_index=True)
    agences = add_lonlat(agences)
    agences = agences.dropna(subset=["lon", "lat"])

    keep = ADMIN_COLS + [
        "nom_localite",
        "etab_nom",
        "etab_adresse",
        "activite_statut",
        "operateur",
        "lon",
        "lat",
    ]
    agences = agences[[c for c in keep if c in agences.columns]]
    log(f"Agences unifiées (Togocom+Moov) : {len(agences)} lignes")
    return agences


def load_canal_plus() -> pd.DataFrame:
    canal = pd.read_csv(RAW / "agences_canal_plus.csv")
    if len(canal) == 0:
        log("Agences CANAL+ : fichier vide (0 ligne) — signalé, aucune donnée à traiter")
    return canal


def load_datacenters() -> pd.DataFrame:
    dc = pd.read_csv(RAW / "datacenters.csv")
    dc = add_lonlat(dc)
    dc = dc.dropna(subset=["lon", "lat"])
    log(f"Datacenters : {len(dc)} lignes")
    return dc


def load_mobile_money() -> pd.DataFrame:
    mm = pd.read_csv(RAW / "agents_mobile_money.csv")
    mm = add_lonlat(mm)
    mm = mm.dropna(subset=["lon", "lat"])
    mm["operateur"] = mm["operateur"].fillna("Nsp")
    log(f"Agents mobile money : {len(mm)} lignes")
    return mm


def load_population() -> pd.DataFrame:
    pop = pd.read_csv(EXTERNAL / "population_prefectures_togo_2022.csv")
    log(f"Population par préfecture (RGPH-5, 2022) : {len(pop)} préfectures, "
        f"{pop['population_totale'].sum():,} habitants".replace(",", " "))
    return pop


def build_prefecture_indicators(agences, mobile_money, population) -> pd.DataFrame:
    nb_agences = (
        agences.groupby("prefecture_nom_bdd").size().rename("nb_agences")
    )
    nb_agences_par_operateur = (
        agences.groupby(["prefecture_nom_bdd", "operateur"]).size().unstack(fill_value=0)
    )
    nb_agences_par_operateur.columns = [f"nb_agences_{c.lower()}" for c in nb_agences_par_operateur.columns]

    nb_mm = (
        mobile_money.groupby("prefecture_nom_bdd").size().rename("nb_agents_mobile_money")
    )

    indic = population.set_index("prefecture").copy()
    indic = indic.join(nb_agences, how="left")
    indic = indic.join(nb_agences_par_operateur, how="left")
    indic = indic.join(nb_mm, how="left")
    indic[["nb_agences", "nb_agents_mobile_money"]] = indic[
        ["nb_agences", "nb_agents_mobile_money"]
    ].fillna(0)
    for c in nb_agences_par_operateur.columns:
        indic[c] = indic[c].fillna(0)

    indic["agences_pour_10k_hab"] = (
        indic["nb_agences"] / indic["population_totale"] * 10_000
    ).round(2)
    indic["agents_mm_pour_10k_hab"] = (
        indic["nb_agents_mobile_money"] / indic["population_totale"] * 10_000
    ).round(2)
    indic["polygon_key"] = [polygon_key(p) for p in indic.index]

    indic = indic.reset_index().rename(columns={"index": "prefecture"})
    log(f"Indicateurs préfecture calculés pour {len(indic)} préfectures")
    return indic


def build_canton_indicators(agences, mobile_money) -> pd.DataFrame:
    nb_agences = agences.groupby(["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd"]).size().rename(
        "nb_agences"
    )
    nb_mm = mobile_money.groupby(["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd"]).size().rename(
        "nb_agents_mobile_money"
    )

    cantons = pd.DataFrame(index=nb_agences.index).join(nb_agences, how="outer")
    cantons = cantons.join(nb_mm, how="outer").fillna(0).reset_index()

    # Centroïde indicatif du canton (moyenne des points connus dans ce canton),
    # utilisé uniquement pour le placement sur la carte — pas une géométrie officielle.
    combined_pts = pd.concat(
        [
            agences[["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd", "lon", "lat"]],
            mobile_money[["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd", "lon", "lat"]],
        ],
        ignore_index=True,
    )
    centroids = combined_pts.groupby(
        ["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd"]
    )[["lon", "lat"]].mean().reset_index()
    cantons = cantons.merge(
        centroids, on=["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd"], how="left"
    )

    # Sur 372 cantons couverts par au moins une donnée, seuls 46 (~12%) ont une
    # agence opérateur physique : "zéro agence" n'est donc PAS un cas rare, c'est
    # la norme. On le garde comme indicateur de présence formelle des opérateurs,
    # et on ajoute un score de priorité qui croise cette absence avec la densité
    # d'agents mobile money (les cantons sans agence ET avec peu d'agents mobile
    # money sont les moins bien desservis numériquement).
    cantons["sans_agence_operateur"] = cantons["nb_agences"] == 0
    cantons["rang_desserte_mm"] = cantons["nb_agents_mobile_money"].rank(method="min")
    cantons["zone_prioritaire"] = (
        cantons["sans_agence_operateur"]
        & (cantons["nb_agents_mobile_money"] <= cantons["nb_agents_mobile_money"].quantile(0.25))
    )

    log(
        f"Indicateurs canton calculés pour {len(cantons)} cantons — "
        f"{int(cantons['sans_agence_operateur'].sum())} sans agence opérateur physique, "
        f"{int(cantons['zone_prioritaire'].sum())} classés zone prioritaire "
        f"(sans agence ET peu d'agents mobile money)"
    )
    return cantons


def build_mobile_money_par_canton(mobile_money: pd.DataFrame) -> pd.DataFrame:
    """Agrège les 19 788 points mobile money par canton (centroïde + effectif),
    pour un affichage carte performant (bulles) plutôt que 19 788 marqueurs individuels."""
    agg = (
        mobile_money.groupby(["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd"])
        .agg(nb_agents=("lon", "size"), lon=("lon", "mean"), lat=("lat", "mean"))
        .reset_index()
    )
    log(f"Mobile money agrégé par canton : {len(agg)} cantons")
    return agg


def build_merged_geojson(prefecture_indicators: pd.DataFrame):
    with open(EXTERNAL / "togo_prefectures_boundaries.geojson", encoding="utf-8") as f:
        geo = json.load(f)

    agg = prefecture_indicators.groupby("polygon_key").agg(
        population_totale=("population_totale", "sum"),
        nb_agences=("nb_agences", "sum"),
        nb_agents_mobile_money=("nb_agents_mobile_money", "sum"),
        prefectures=("prefecture", lambda s: " + ".join(sorted(s))),
    ).reset_index()
    agg["agences_pour_10k_hab"] = (agg["nb_agences"] / agg["population_totale"] * 10_000).round(2)
    agg["agents_mm_pour_10k_hab"] = (
        agg["nb_agents_mobile_money"] / agg["population_totale"] * 10_000
    ).round(2)
    agg["densite_pop_indicative"] = agg["population_totale"]  # densité réelle nécessiterait la surface

    lookup = agg.set_index("polygon_key").to_dict(orient="index")

    matched = 0
    for feature in geo["features"]:
        name = feature["properties"].get("shapeName")
        group = shape_group_key(name)
        if group in lookup:
            feature["properties"].update(lookup[group])
            matched += 1
        else:
            feature["properties"].update(
                {
                    "population_totale": None,
                    "nb_agences": None,
                    "nb_agents_mobile_money": None,
                    "prefectures": None,
                    "agences_pour_10k_hab": None,
                    "agents_mm_pour_10k_hab": None,
                }
            )

    log(f"GeoJSON enrichi : {matched}/{len(geo['features'])} polygones associés à des indicateurs")
    return geo


def main():
    agences = load_agences()
    canal = load_canal_plus()
    datacenters = load_datacenters()
    mobile_money = load_mobile_money()
    population = load_population()

    prefecture_indicators = build_prefecture_indicators(agences, mobile_money, population)
    canton_indicators = build_canton_indicators(agences, mobile_money)
    mm_par_canton = build_mobile_money_par_canton(mobile_money)
    merged_geojson = build_merged_geojson(prefecture_indicators)

    agences.to_csv(PROCESSED / "agences_unifiees.csv", index=False)
    canal.to_csv(PROCESSED / "agences_canal_plus.csv", index=False)
    datacenters.to_csv(PROCESSED / "datacenters.csv", index=False)
    mobile_money.to_csv(PROCESSED / "mobile_money_agents.csv", index=False)
    prefecture_indicators.to_csv(PROCESSED / "indicateurs_prefecture.csv", index=False)
    canton_indicators.to_csv(PROCESSED / "indicateurs_canton.csv", index=False)
    mm_par_canton.to_csv(PROCESSED / "mobile_money_par_canton.csv", index=False)
    with open(PROCESSED / "prefectures_merged.geojson", "w", encoding="utf-8") as f:
        json.dump(merged_geojson, f, ensure_ascii=False)

    log("Pipeline terminé. Fichiers écrits dans data/processed/")


if __name__ == "__main__":
    main()
