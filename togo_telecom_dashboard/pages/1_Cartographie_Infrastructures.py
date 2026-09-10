import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import COLORS, get_agences, get_datacenters, get_mobile_money_par_canton
from src.style_loader import filter_title, inject_styles, sidebar_brand
from src.utils import format_int

st.set_page_config(page_title="Cartographie — Infrastructures", page_icon="🗺️", layout="wide")

inject_styles()
sidebar_brand()

st.title("🗺️ Cartographie des infrastructures télécoms")
st.caption(
    "Répartition spatiale des agences Togocom / Moov, des datacenters et des agents "
    "mobile money (agrégés par canton). Utilisez les filtres pour vous concentrer sur "
    "une zone ou un opérateur."
)

with st.spinner("Chargement des données…"):
    agences = get_agences()
    datacenters = get_datacenters()
    mm_canton = get_mobile_money_par_canton()

# ---------------------------------------------------------------- Filtres
filter_title()

regions = sorted(agences["region_nom_bdd"].dropna().unique())
region_sel = st.sidebar.multiselect("Région", regions, default=regions)

prefectures_dispo = sorted(
    agences.loc[agences["region_nom_bdd"].isin(region_sel), "prefecture_nom_bdd"].dropna().unique()
)
prefecture_sel = st.sidebar.multiselect("Préfecture", prefectures_dispo, default=prefectures_dispo)

operateurs = sorted(agences["operateur"].dropna().unique())
operateur_sel = st.sidebar.multiselect("Opérateur (agences)", operateurs, default=operateurs)

st.sidebar.markdown("---")
show_agences = st.sidebar.checkbox("Afficher les agences opérateurs", value=True)
show_dc = st.sidebar.checkbox("Afficher les datacenters", value=True)
show_mm = st.sidebar.checkbox("Afficher les agents mobile money (par canton)", value=True)

# ---------------------------------------------------------------- Application des filtres
agences_f = agences[
    agences["region_nom_bdd"].isin(region_sel)
    & agences["prefecture_nom_bdd"].isin(prefecture_sel)
    & agences["operateur"].isin(operateur_sel)
]
dc_f = datacenters[
    datacenters["region_nom_bdd"].isin(region_sel) & datacenters["prefecture_nom_bdd"].isin(prefecture_sel)
]
mm_f = mm_canton[
    mm_canton["region_nom_bdd"].isin(region_sel) & mm_canton["prefecture_nom_bdd"].isin(prefecture_sel)
]

c1, c2, c3 = st.columns(3)
c1.metric("Agences affichées", format_int(len(agences_f)))
c2.metric("Datacenters affichés", format_int(len(dc_f)))
c3.metric("Agents mobile money (zone filtrée)", format_int(int(mm_f["nb_agents"].sum())))

# ---------------------------------------------------------------- Empty states
has_layers = (show_agences and len(agences_f)) or (show_dc and len(dc_f)) or (show_mm and len(mm_f))
if not region_sel:
    st.warning("Sélectionnez au moins une région dans la barre latérale pour afficher les données.")
elif not has_layers:
    st.info("Aucune donnée à afficher pour les filtres sélectionnés. Essayez d'élargir votre sélection de région, préfecture ou opérateur.")

# ---------------------------------------------------------------- Carte
fig = px.scatter_map(
    lat=[], lon=[],
    zoom=6.2, center={"lat": 8.6, "lon": 1.0}, height=650,
)

if show_mm and len(mm_f):
    bubble = px.scatter_map(
        mm_f,
        lat="lat", lon="lon", size="nb_agents", size_max=38,
        color_discrete_sequence=[COLORS["Mobile money"]],
        hover_name="canton_nom_bdd",
        hover_data={"prefecture_nom_bdd": True, "nb_agents": True, "lat": False, "lon": False},
    )
    for tr in bubble.data:
        tr.name = "Mobile money (par canton)"
        tr.showlegend = True
        tr.marker.opacity = 0.45
        fig.add_trace(tr)

if show_agences and len(agences_f):
    for op in agences_f["operateur"].unique():
        sub = agences_f[agences_f["operateur"] == op]
        tr = px.scatter_map(sub, lat="lat", lon="lon", hover_name="etab_nom").data[0]
        tr.name = f"Agence {op}"
        tr.showlegend = True
        tr.marker.color = COLORS.get(op, "#333333")
        tr.marker.size = 11
        fig.add_trace(tr)

if show_dc and len(dc_f):
    tr = px.scatter_map(dc_f, lat="lat", lon="lon", hover_name="etab_nom").data[0]
    tr.name = "Datacenter"
    tr.showlegend = True
    tr.marker.color = COLORS["Datacenter"]
    tr.marker.size = 16
    tr.marker.symbol = "circle"
    fig.add_trace(tr)

fig.update_layout(
    map_style="carto-positron",
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- Tableau
st.markdown("#### Détail des agences affichées")

df_table = agences_f[
    ["operateur", "region_nom_bdd", "prefecture_nom_bdd", "commune_nom_bdd",
     "canton_nom_bdd", "etab_nom", "etab_adresse"]
].rename(columns={
    "operateur": "Opérateur", "region_nom_bdd": "Région", "prefecture_nom_bdd": "Préfecture",
    "commune_nom_bdd": "Commune", "canton_nom_bdd": "Canton", "etab_nom": "Agence",
    "etab_adresse": "Adresse",
})

if df_table.empty:
    st.info("Aucune agence ne correspond aux filtres sélectionnés.")
else:
    st.dataframe(
        df_table,
        width="stretch",
        height=300,
        column_config={
            "Opérateur": st.column_config.TextColumn(width="small"),
            "Région": st.column_config.TextColumn(width="small"),
            "Préfecture": st.column_config.TextColumn(width="small"),
            "Commune": st.column_config.TextColumn(width="medium"),
            "Canton": st.column_config.TextColumn(width="medium"),
            "Agence": st.column_config.TextColumn(width="medium"),
            "Adresse": st.column_config.TextColumn(width="large"),
        },
        hide_index=True,
    )
