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
    chargé mais signalé comme tel plutôt qu'ignoré silencieusement. Les
    points de vente CANAL+ réels (API canalbox.tg + OpenStreetMap) sont
    ajoutés depuis data/external/canal_points.csv (couche "externe",
    distinguée des données BDD, ne pas dédoublonner avec Togocom/Moov).
  - La population est disponible officiellement au niveau PRÉFECTURE et au
    niveau CANTON (RGPH-5, INSEED 2022). La population canton provient de
    l'extraction INSEED (pages 51-107 du Livret 01), appariée aux cantons
    BDD par (préfecture, nom) : 361/370 cantons INSEED ont un polygone HDX,
    les cantons BDD de Golfe/Agoè-Nyivé/Danyi n'ont pas de population canton
    (publiés par quartiers/communes) -> colonnes population_* NaN.
  - Les polygones préfecture proviennent désormais de HDX OCHA COD-AB
    (40 préfectures, y compris les scissions 2021), regroupés sous les
    mêmes clés que les indicateurs préfecture.
"""
from pathlib import Path
import json
import sys
import zipfile
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import add_lonlat, norm_name, polygon_key  # noqa: E402

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

POPULATION_COLS = ["population_totale", "population_masculin", "population_feminin"]

# Préfecture BDD -> préfecture INSEED (libellés de l'extraction PDF)
PREF_ALIASES = {
    "Kpendjal-Ouest": "Kpendjal-Ouest",
    "Mô": "Mô",
}


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


def load_canton_population() -> pd.DataFrame:
    """Population par canton (RGPH-5, INSEED 2022) jointe aux cantons ADM3 HDX."""
    return pd.read_csv(EXTERNAL / "canton_population_join.csv")


def load_canal_plus_external() -> pd.DataFrame:
    """Points de vente CANAL+ réels (API canalbox.tg + OpenStreetMap).
    Donnée EXTERNE (hors BDD) : ne pas confondre ni fusionner avec les
    agences Togocom/Moov."""
    df = pd.read_csv(EXTERNAL / "canal_points.csv")
    log(f"Points CANAL+ (externe : canalbox + OSM) : {len(df)} lignes")
    return df


def match_canton_population(cantons: pd.DataFrame, pop_join: pd.DataFrame) -> pd.DataFrame:
    """Ajoute aux indicateurs canton la population RGPH-5 (par préfecture+nom,
    normalisés, puis fuzzy dans la même préfecture).

    Nouveaux champs : population_totale / _masculin / _feminin (NaN si non
    disponible), population_method (exact|fuzzy|non_disponible) et métadonnées
    ADM3 (adm3_pcode, adm3_name_hdx, adm2_name_hdx) pour la cartographie.
    """
    cantons = cantons.copy()
    for c in POPULATION_COLS:
        cantons[c] = pd.NA
    cantons["population_method"] = "non_disponible"
    cantons["adm2_name_hdx"] = None
    cantons["adm3_name_hdx"] = None
    cantons["adm3_pcode_hdx"] = None
    cantons["area_sqkm_hdx"] = None

    if pop_join is None or len(pop_join) == 0:
        log("Population canton : aucune donnée INSEED — indicateurs canton inchangés")
        return cantons

    pj = pop_join.copy()
    pj["_key"] = (
        pj["prefecture_pdf"].apply(norm_name) + "|" + pj["canton_pdf"].apply(norm_name)
    )
    exact = pj.drop_duplicates("_key").set_index("_key")
    by_pref = {p: g for p, g in pj.groupby(pj["prefecture_pdf"].apply(norm_name))}

    n_exact = n_fuzzy = 0
    for idx, row in cantons.iterrows():
        pref_norm = norm_name(row["prefecture_nom_bdd"])
        canton_norm = norm_name(row["canton_nom_bdd"])
        key = pref_norm + "|" + canton_norm
        hit = exact.loc[key] if key in exact.index else None
        method = "exact"
        if hit is None:
            pool = by_pref.get(pref_norm)
            best = None
            if pool is not None and len(pool):
                best = process.extractOne(
                    canton_norm, pool["canton_pdf"].apply(norm_name).tolist(),
                    scorer=fuzz.WRatio, score_cutoff=88,
                )
            if best and best[1] > 85:
                hit = pool.iloc[best[2]]
                method = "fuzzy"
            else:
                continue
        cantons.at[idx, "population_totale"] = hit["population_totale"]
        cantons.at[idx, "population_masculin"] = hit["masculin"]
        cantons.at[idx, "population_feminin"] = hit["feminin"]
        cantons.at[idx, "population_method"] = method
        cantons.at[idx, "adm2_name_hdx"] = hit.get("adm2_name")
        cantons.at[idx, "adm3_name_hdx"] = hit.get("adm3_name")
        cantons.at[idx, "adm3_pcode_hdx"] = hit.get("adm3_pcode")
        cantons.at[idx, "area_sqkm_hdx"] = hit.get("area_sqkm")
        n_exact += method == "exact"
        n_fuzzy += method == "fuzzy"

    pop_attached = int(cantons["population_totale"].sum(skipna=True))
    log(
        f"Population canton attachée à {n_exact + n_fuzzy} cantons BDD "
        f"({n_exact} exact, {n_fuzzy} fuzzy), couverture population = "
        f"{pop_attached:,} hab.".replace(",", " ")
    )
    return cantons


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


def build_canton_indicators(agences, mobile_money, canton_population: Optional[pd.DataFrame] = None) -> pd.DataFrame:
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
    if canton_population is not None:
        cantons = match_canton_population(cantons, canton_population)
        cantons = enrich_per_capita(cantons)
    return cantons


def enrich_per_capita(cantons: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les indicateurs "par habitant" (population RGPH-5 canton) :
    densité de population (surface ADM3 HDX), agences et agents mobile money
    pour 10 000 habitants. Colonnes NaN lorsque la population est indisponible."""
    pop = pd.to_numeric(cantons["population_totale"], errors="coerce")
    densite = pop / pd.to_numeric(cantons["area_sqkm_hdx"], errors="coerce")
    cantons["densite_pop_par_km2"] = densite.round(1)
    cantons["agences_pour_10k_hab"] = (cantons["nb_agences"] / pop * 10_000).round(2)
    cantons["agents_mm_pour_10k_hab"] = (cantons["nb_agents_mobile_money"] / pop * 10_000).round(2)
    return cantons


def analyse_cantons_per_capita(cantons: pd.DataFrame) -> dict:
    """Analyse croisée population / desserte au niveau canton (P1.1) :
    - population totale couverte par les cantons avec population connu ;
    - population vivant dans les cantons "zone prioritaire" ;
    - population vivant dans des cantons SANS aucun agent mobile money ;
    - top entre-deux : cantons les plus peuplés sans aucun agent mobile money.
    Retourne un résumé (dict) pour le log et la page Recommandations."""
    has_pop = cantons["population_totale"].notna()
    pop_connue = cantons.loc[has_pop, "population_totale"].sum()
    zonas = cantons.loc[has_pop & cantons["zone_prioritaire"], "population_totale"].sum()
    sans_agence = cantons.loc[has_pop & cantons["sans_agence_operateur"], "population_totale"].sum()
    top_fort = (
        cantons.loc[has_pop & cantons["sans_agence_operateur"]]
        .sort_values("population_totale", ascending=False)
        .head(10)[["prefecture_nom_bdd", "canton_nom_bdd", "population_totale", "nb_agents_mobile_money"]]
        .to_dict(orient="records")
    )
    return {
        "population_canton_connue": int(pop_connue),
        "population_zone_prioritaire": int(zonas),
        "population_sans_agence_operateur": int(sans_agence),
        "top_cantons_peuples_sans_agence": top_fort,
    }


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


# Correspondance des 40 préfectures HDX (COD-AB) vers les préfectures BDD
HDX_ADM2_TO_PREF = {
    "Agoe-Nyive": "Agoè-Nyivé", "Agou": "Agou", "Akebou": "Akébou",
    "Amou": "Amou", "Anie": "Anié", "Assoli": "Assoli", "Ave": "Avé",
    "Bas-Mono": "Bas-Mono", "Bassar": "Bassar", "Binah": "Binah",
    "Blitta": "Blitta", "Cinkasse": "Cinkassé", "Dankpen": "Dankpen",
    "Danyi": "Danyi", "Doufelgou": "Doufelgou", "Est-Mono": "Est-Mono",
    "Golfe": "Golfe", "Haho": "Haho", "Keran": "Kéran", "Kloto": "Kloto",
    "Kozah": "Kozah", "Kpele": "Kpélé", "Kpendjal": "Kpendjal",
    "Lacs": "Lacs", "Lome Commune": "Golfe", "Moyen-Mono": "Moyen-Mono",
    "Naki-Ouest": "Naki-Ouest", "Ogou": "Ogou", "Oti": "Oti",
    "Oti-Sud": "Oti-Sud", "Plaine du Mo": "Mô",
    "Sotouboua": "Sotouboua", "Tandjoare": "Tandjoaré", "Tchamba": "Tchamba",
    "Tchaoudjo": "Tchaoudjo", "Tone": "Tône", "Vo": "Vo", "Wawa": "Wawa",
    "Yoto": "Yoto", "Zio": "Zio",
}


def _load_hdx_adm2_geojson() -> dict:
    """Charge le geojson ADM2 HDX (OCHA COD-AB) depuis l'archive gitignorée."""
    with zipfile.ZipFile(EXTERNAL / "tgo_admin_boundaries.geojson.zip") as z:
        with z.open("tgo_admin2.geojson") as fh:
            return json.load(fh)


def build_merged_geojson(prefecture_indicators: pd.DataFrame) -> dict:
    """Construit le geojson préfecture à partir des polygones officiels HDX
    (40 préfectures, scissions 2021 incluses), regroupés sous la même clé
    `polygon_key` que les indicateurs préfecture (>contrat de la page carte)."""
    geo = _load_hdx_adm2_geojson()

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
    agg["densite_pop_indicative"] = agg["population_totale"]

    lookup = {k: v for k, v in zip(agg["polygon_key"], agg.to_dict(orient="records"))}

    # Rassemblement des géométries HDX par clé de groupe
    groups: dict[str, dict] = {}
    areas: dict[str, float] = {}
    for feature in geo["features"]:
        props = feature.get("properties", {})
        name = props.get("adm2_name")
        pref = HDX_ADM2_TO_PREF.get(name, name)
        key = polygon_key(pref)
        groups.setdefault(key, {"geoms": [], "names": []})["names"].append(name)
        groups[key]["geoms"].append(feature["geometry"])
        area = props.get("area_sqkm")
        if area is not None:
            areas[key] = areas.get(key, 0.0) + float(area)

    out = {"type": "FeatureCollection", "features": []}
    matched = 0
    for key, info in groups.items():
        coords = []
        for g in info["geoms"]:
            if g.get("type") == "Polygon":
                coords.append(g["coordinates"])
            elif g.get("type") == "MultiPolygon":
                coords.extend(g["coordinates"])
        props = {
            "shapeName": key,
            "shape_group_key": key,
            "shapeType": "MultiPolygon",
            "hdx_adm2": " + ".join(sorted(set(info["names"]))),
        }
        if key in lookup:
            props.update(lookup[key])
            matched += 1
        else:
            props.update(
                {
                    "population_totale": None, "nb_agences": None,
                    "nb_agents_mobile_money": None, "prefectures": None,
                    "agences_pour_10k_hab": None, "agents_mm_pour_10k_hab": None,
                }
            )
        pop = props.get("population_totale")
        area = areas.get(key)
        props["densite_pop_par_km2"] = (
            round(pop / area, 1) if pop is not None and area else None
        )
        out["features"].append(
            {"type": "Feature", "properties": props, "geometry": {"type": "MultiPolygon", "coordinates": coords}}
        )

    log(f"GeoJSON HDX enrichi : {matched}/{len(out['features'])} polygones associés à des indicateurs")
    return out


def main():
    agences = load_agences()
    canal = load_canal_plus()
    canal_external = load_canal_plus_external()
    datacenters = load_datacenters()
    mobile_money = load_mobile_money()
    population = load_population()
    canton_population = load_canton_population()

    prefecture_indicators = build_prefecture_indicators(agences, mobile_money, population)
    canton_indicators = build_canton_indicators(agences, mobile_money, canton_population)
    if "population_totale" in canton_indicators and canton_indicators["population_totale"].notna().any():
        an = analyse_cantons_per_capita(canton_indicators)
        log("Analyse canton per capita : population connue = "
            f"{an['population_canton_connue']:,}".replace(",", " "))
        log(f"  - population en zone prioritaire : {an['population_zone_prioritaire']:,}".replace(",", " "))
        log(f"  - population sans agence opérateur : {an['population_sans_agence_operateur']:,}".replace(",", " "))
        log("  - cantons les plus peuplés sans agence opérateur :")
        for r in an["top_cantons_peuples_sans_agence"][:6]:
            log(f"    * {r['canton_nom_bdd']} ({r['prefecture_nom_bdd']}) — "
                f"{r['population_totale']:,} hab., {r['nb_agents_mobile_money']} agents MM".replace(",", " "))
    mm_par_canton = build_mobile_money_par_canton(mobile_money)
    merged_geojson = build_merged_geojson(prefecture_indicators)

    agences.to_csv(PROCESSED / "agences_unifiees.csv", index=False)
    canal.to_csv(PROCESSED / "agences_canal_plus.csv", index=False)
    canal_external.to_csv(PROCESSED / "canal_points.csv", index=False)
    datacenters.to_csv(PROCESSED / "datacenters.csv", index=False)
    mobile_money.to_csv(PROCESSED / "mobile_money_agents.csv", index=False)
    prefecture_indicators.to_csv(PROCESSED / "indicateurs_prefecture.csv", index=False)
    canton_indicators.to_csv(PROCESSED / "indicateurs_canton.csv", index=False)
    mm_par_canton.to_csv(PROCESSED / "mobile_money_par_canton.csv", index=False)
    # Cantons ADM3 HDX (centroïdes officiels) pour la cartographie canton (P2)
    pd.read_csv(EXTERNAL / "tgo_admin3_cantons.csv").to_csv(
        PROCESSED / "cantons_hdx.csv", index=False
    )
    with open(PROCESSED / "prefectures_merged.geojson", "w", encoding="utf-8") as f:
        json.dump(merged_geojson, f, ensure_ascii=False)

    log("Pipeline terminé. Fichiers écrits dans data/processed/")


if __name__ == "__main__":
    main()
