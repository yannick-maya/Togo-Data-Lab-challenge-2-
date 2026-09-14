"""
Chargement (avec cache Streamlit) des données préparées par src/data_pipeline.py.
Toutes les pages de l'application importent leurs données depuis ce module,
afin de ne lire les fichiers qu'une seule fois par session.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# Palette de couleurs cohérente utilisée sur toutes les pages
COLORS = {
    "Togocom": "#F7B500",       # jaune Togocom
    "Moov": "#E30613",          # rouge Moov
    "Mobile money": "#0072BC",
    "Datacenter": "#6A2C91",
    "CANAL+ (externe)": "#F72585",
    "Zone prioritaire": "#D7263D",
    "Bonne desserte": "#1B998B",
}


def _ensure_processed():
    if not PROCESSED.exists() or not any(PROCESSED.iterdir()):
        st.error(
            "Les données préparées sont introuvables dans `data/processed/`.\n\n"
            "Lancez d'abord le pipeline depuis la racine du projet :\n\n"
            "```\npython src/data_pipeline.py\n```"
        )
        st.stop()


@st.cache_data
def get_agences() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "agences_unifiees.csv")


@st.cache_data
def get_mobile_money() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "mobile_money_agents.csv")


@st.cache_data
def get_datacenters() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "datacenters.csv")


@st.cache_data
def get_canal_plus() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "agences_canal_plus.csv")


@st.cache_data
def get_canal_plus_external() -> pd.DataFrame:
    """Points de vente CANAL+ réels (couche EXTERNE : API canalbox.tg + OSM).
    Distincte de `get_canal_plus()` (fichier BDD vide) et DES AGENCES Togocom/Moov."""
    _ensure_processed()
    return pd.read_csv(PROCESSED / "canal_points.csv")


@st.cache_data
def get_cantons_hdx() -> pd.DataFrame:
    """Cantons ADM3 HDX (centroïdes officiels + surfaces) pour la cartographie canton."""
    _ensure_processed()
    return pd.read_csv(PROCESSED / "cantons_hdx.csv")


@st.cache_data
def get_mobile_money_par_canton() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "mobile_money_par_canton.csv")


@st.cache_data
def get_prefecture_indicators() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "indicateurs_prefecture.csv")


@st.cache_data
def get_canton_indicators() -> pd.DataFrame:
    _ensure_processed()
    return pd.read_csv(PROCESSED / "indicateurs_canton.csv")


@st.cache_data
def get_geojson() -> dict:
    _ensure_processed()
    with open(PROCESSED / "prefectures_merged.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def get_kpis() -> dict:
    """Quelques chiffres-clés nationaux calculés une seule fois pour la page d'accueil."""
    agences = get_agences()
    mm = get_mobile_money()
    dc = get_datacenters()
    pref = get_prefecture_indicators()
    cantons = get_canton_indicators()
    return {
        "population_totale": int(pref["population_totale"].sum()),
        "nb_agences": len(agences),
        "nb_agences_togocom": int((agences["operateur"] == "Togocom").sum()),
        "nb_agences_moov": int((agences["operateur"] == "Moov").sum()),
        "nb_agents_mm": len(mm),
        "nb_datacenters": len(dc),
        "nb_prefectures": len(pref),
        "nb_prefectures_sans_agence": int((pref["nb_agences"] == 0).sum()),
        "nb_cantons": len(cantons),
        "nb_cantons_sans_agence": int(cantons["sans_agence_operateur"].sum()),
        "nb_cantons_prioritaires": int(cantons["zone_prioritaire"].sum()),
    }
