import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.components.filter_bar import filter_bar
from src.data_loader import COLORS, get_agences, get_canal_plus_external, get_datacenters, get_mobile_money_par_canton
from src.style_loader import FAVICON, MAP_STYLE, THEME, hero, inject_styles, page_header, region_color_map, sidebar_brand, style_figure
from src.utils import format_int

st.set_page_config(page_title="Cartographie — Infrastructures", page_icon=FAVICON, layout="wide")

inject_styles()
sidebar_brand()

st.markdown(
    page_header(
        "map",
        "Cartographie des infrastructures télécoms",
        "Répartition spatiale des agences Togocom / Moov, des datacenters et des agents "
        "mobile money (agrégés par canton). Utilisez les filtres pour vous concentrer sur "
        "une zone ou un opérateur.",
    ),
    unsafe_allow_html=True,
)

with st.spinner("Chargement des données…"):
    agences = get_agences()
    datacenters = get_datacenters()
    mm_canton = get_mobile_money_par_canton()
    canal = get_canal_plus_external()

# ---------------------------------------------------------------- Filtres (bandeau partagé)
filtres = filter_bar(
    region=True, prefecture=True, operateur=True, layers=True,
    region_options=lambda: sorted(agences["region_nom_bdd"].dropna().unique()),
    prefecture_options=lambda rsel: agences.loc[
        agences["region_nom_bdd"].isin(rsel), "prefecture_nom_bdd"
    ].dropna().unique(),
)
region_sel, prefecture_sel, operateur_sel = filtres.region, filtres.prefecture, filtres.operateur
show_agences = filtres.layers["agences"]
show_dc = filtres.layers["dc"]
show_mm = filtres.layers["mm"]
show_canal = filtres.layers["canal"]

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

col_hero, col_rest = st.columns([1, 2], gap="medium")
with col_hero:
    st.markdown(
        hero(
            label="Agences affichées (zone filtrée)",
            value=format_int(len(agences_f)),
            unit="pts",
            tone="accent",
            note="Agences Togocom et Moov",
        ),
        unsafe_allow_html=True,
    )
with col_rest:
    c2, c3 = st.columns(2)
    c2.metric("Datacenters affichés", format_int(len(dc_f)))
    c3.metric("Agents mobile money (zone filtrée)", format_int(int(mm_f["nb_agents"].sum())))

# ---------------------------------------------------------------- Empty states
has_layers = (show_agences and len(agences_f)) or (show_dc and len(dc_f)) or (show_mm and len(mm_f)) or (show_canal and len(canal))
if not region_sel:
    st.warning("Sélectionnez au moins une région dans le bandeau de filtres pour afficher les données.")
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
        tr.marker.color = COLORS.get(op, THEME["text_secondary"])
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

if show_canal and len(canal):
    tr = px.scatter_map(
        canal, lat="lat", lon="lon",
        hover_name="name",
        hover_data={"commune": True, "type": True, "source": True, "lat": False, "lon": False},
    ).data[0]
    tr.name = "CANAL+ (externe)"
    tr.showlegend = True
    tr.marker.color = COLORS["CANAL+ (externe)"]
    tr.marker.size = 9
    tr.marker.symbol = "square"
    fig.add_trace(tr)

fig.update_layout(
    map_style=MAP_STYLE,
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", font=dict(color=THEME["text_secondary"])),
)
style_figure(fig)
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------- Répartition régionale
st.markdown("#### Agences par région : volume brut et part nationale")
st.caption(
    "Mêmes couleurs par région que sur les autres pages (ordre alphabétique stable). "
    "À gauche le nombre d'agences affichées, à droite leur part dans le total national."
)

agg_region = (
    agences_f.groupby("region_nom_bdd")["etab_nom"]
    .count()
    .rename("nb")
    .sort_values(ascending=False)
)
region_pal = region_color_map()

col_reg, col_part = st.columns([1.1, 1], gap="medium")

with col_reg:
    agg_region_df = agg_region.rename_axis("region").reset_index(name="nb")
    fig_reg = px.bar(
        agg_region_df,
        x="nb",
        y="region",
        orientation="h",
        color="region",
        color_discrete_map=region_pal,
        labels={"nb": "Nombre d'agences", "region": ""},
        height=max(280, 60 + 40 * len(agg_region)),
    )
    fig_reg.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    style_figure(fig_reg)
    st.plotly_chart(fig_reg, width="stretch")

with col_part:
    fig_part = px.pie(
        values=agg_region.values,
        names=agg_region.index,
        hole=0.58,
        color=agg_region.index,
        color_discrete_map=region_pal,
    )
    fig_part.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=11)),
    )
    fig_part.update_traces(
        textinfo="percent",
        textfont=dict(size=13, color=THEME["text_primary"]),
        textposition="inside",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    style_figure(fig_part)
    st.plotly_chart(fig_part, width="stretch")
    st.caption("Part des agences affichées par région (%).")

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
