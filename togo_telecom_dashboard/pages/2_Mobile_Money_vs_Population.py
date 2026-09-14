import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.express as px
import streamlit as st

from src.data_loader import get_geojson, get_prefecture_indicators
from src.style_loader import filter_title, inject_styles, sidebar_brand
from src.utils import format_int, gini_coefficient, lorenz_curve

st.set_page_config(page_title="Mobile money vs population", page_icon="📱", layout="wide")

inject_styles()
sidebar_brand()

st.title("📱 Couverture mobile money et adéquation avec la population")
st.caption(
    "Les points mobile money sont-ils répartis proportionnellement à la population, "
    "ou certaines préfectures très peuplées restent-elles sous-équipées ?"
)

with st.spinner("Chargement des indicateurs par préfecture…"):
    pref = get_prefecture_indicators()
    geo = get_geojson()

regions = sorted(pref["region"].unique())
filter_title()
region_sel = st.sidebar.multiselect("Région", regions, default=regions)
pref_f = pref[pref["region"].isin(region_sel)].copy()

if pref_f.empty:
    st.warning("Aucune préfecture ne correspond à la région sélectionnée. Modifiez le filtre dans la barre latérale.")
    st.stop()

st.markdown("#### Carte — agents mobile money pour 10 000 habitants, par préfecture")
st.caption(
    "Préfectures issues d'une scission récente regroupées par bloc (Grand Lomé : "
    "Golfe + Agoè-Nyivé ; Kpendjal + Kpendjal-Ouest ; Oti + Oti-Sud) pour garder "
    "une clé stable sur toutes les pages. Les polygones proviennent des frontières "
    "officielles HDX (OCHA COD-AB), qui fournit un tracé séparé pour les préfectures "
    "scindées en 2021."
)

with st.spinner("Construction de la carte choroplèthe…"):
    fig_map = px.choropleth_map(
        pref_f,
        geojson=geo,
        locations="polygon_key",
        featureidkey="properties.shapeName",
        color="agents_mm_pour_10k_hab",
        color_continuous_scale="Blues",
        map_style="carto-positron",
        zoom=6.2,
        center={"lat": 8.6, "lon": 1.0},
        opacity=0.8,
        height=560,
        hover_name="prefecture",
        hover_data={"population_totale": True, "nb_agents_mobile_money": True, "polygon_key": False},
        labels={"agents_mm_pour_10k_hab": "Agents / 10k hab."},
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_map, width="stretch")

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("#### Classement des préfectures (agents pour 10 000 hab.)")
    ranked = pref_f.sort_values("agents_mm_pour_10k_hab")
    fig_bar = px.bar(
        ranked,
        x="agents_mm_pour_10k_hab",
        y="prefecture",
        orientation="h",
        color="region",
        height=max(400, len(ranked) * 28),
        labels={"agents_mm_pour_10k_hab": "Agents mobile money / 10 000 hab.", "prefecture": ""},
    )
    fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.01))
    st.plotly_chart(fig_bar, width="stretch")

with col2:
    st.markdown("#### Population vs nombre d'agents mobile money")
    st.caption(
        "Chaque point est une préfecture. Sous la ligne pointillée = moins bien "
        "desservie que la moyenne nationale rapportée à sa population."
    )
    moyenne_nationale = pref_f["nb_agents_mobile_money"].sum() / pref_f["population_totale"].sum()
    fig_sc = px.scatter(
        pref_f,
        x="population_totale",
        y="nb_agents_mobile_money",
        color="region",
        size="population_totale",
        hover_name="prefecture",
        height=max(400, len(pref_f) * 32),
        labels={"population_totale": "Population (2022)", "nb_agents_mobile_money": "Agents mobile money"},
    )
    xmax = pref_f["population_totale"].max()
    fig_sc.add_shape(
        type="line", x0=0, y0=0, x1=xmax, y1=xmax * moyenne_nationale,
        line=dict(dash="dash", color="gray"),
    )
    st.plotly_chart(fig_sc, width="stretch")

st.divider()

# ---------------------------------------------------------------- Lorenz / Gini
st.markdown("#### Inégalités de répartition : courbes de Lorenz et Gini")
st.caption(
    "Préfectures triées par ratio équipement / population croissant. Une courbe loin "
    "de la bissectrice = répartition très inégale : une grande part de la population "
    "vit dans des préfectures relativement peu dotées. Les préfectures sans aucun "
    "opérateur (agences) tirent fortement la courbe des agences vers le bas."
)

gini_agences = gini_coefficient(pref_f["nb_agences"], pref_f["population_totale"])
gini_mm = gini_coefficient(pref_f["nb_agents_mobile_money"], pref_f["population_totale"])

p_pts_a, e_pts_a = lorenz_curve(pref_f["nb_agences"], pref_f["population_totale"])
p_pts_m, e_pts_m = lorenz_curve(pref_f["nb_agents_mobile_money"], pref_f["population_totale"])

n1, n2, n3 = st.columns(3)
n1.metric("Gini — agences opérateurs", f"{gini_agences:.3f}",
          help="0 = proportionnel à la population · 1 = totalement concentré")
n2.metric("Gini — agents mobile money", f"{gini_mm:.3f}",
          help="0 = proportionnel à la population · 1 = totalement concentré")
n3.metric(
    "Interprétation",
    "Très inégal" if max(gini_agences, gini_mm) > 0.5 else "Modérément inégal",
    delta="agences ≫ mobile money" if gini_agences > gini_mm else "mobile money ≫ agences",
    delta_color="off",
)

if p_pts_a is not None:
    fig_lorenz = px.line(x=[0, 1], y=[0, 1], labels={"x": "Part cumulée de la population", "y": "Part cumulée de l'équipement"})
    fig_lorenz.add_trace(
        px.line(x=np.concatenate([[0], p_pts_a.to_numpy()]), y=np.concatenate([[0], e_pts_a.to_numpy()])).data[0]
    )
    fig_lorenz.data[0].name = "Agences opérateurs"
    fig_lorenz.add_trace(
        px.line(x=np.concatenate([[0], p_pts_m.to_numpy()]), y=np.concatenate([[0], e_pts_m.to_numpy()])).data[0]
    )
    fig_lorenz.data[1].name = "Agents mobile money"
    fig_lorenz.data[0].line.color = "#333333"
    fig_lorenz.data[1].line.color = "#0072BC"
    fig_lorenz.update_layout(
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        xaxis=dict(range=[0, 1.02]), yaxis=dict(range=[0, 1.02]),
        showlegend=True,
    )
    st.plotly_chart(fig_lorenz, width="stretch")
else:
    st.info("Pas assez de données pour tracer la courbe de Lorenz sur la zone filtrée.")

# ---------------------------------------------------------------- Tableau
st.markdown("#### Table détaillée")

df_table = pref_f[
    ["region", "prefecture", "population_totale", "nb_agences", "nb_agents_mobile_money",
     "agences_pour_10k_hab", "agents_mm_pour_10k_hab"]
].rename(columns={
    "region": "Région", "prefecture": "Préfecture", "population_totale": "Population",
    "nb_agences": "Nb agences", "nb_agents_mobile_money": "Nb agents MM",
    "agences_pour_10k_hab": "Agences / 10k hab.", "agents_mm_pour_10k_hab": "Agents MM / 10k hab.",
}).sort_values("Agents MM / 10k hab.")

st.dataframe(
    df_table,
    width="stretch",
    height=340,
    column_config={
        "Région": st.column_config.TextColumn(width="small"),
        "Préfecture": st.column_config.TextColumn(width="medium"),
        "Population": st.column_config.NumberColumn(width="medium", format="%d"),
        "Nb agences": st.column_config.NumberColumn(width="small", format="%d"),
        "Nb agents MM": st.column_config.NumberColumn(width="small", format="%d"),
        "Agences / 10k hab.": st.column_config.NumberColumn(width="medium", format="%.2f"),
        "Agents MM / 10k hab.": st.column_config.NumberColumn(width="medium", format="%.2f"),
    },
    hide_index=True,
)
