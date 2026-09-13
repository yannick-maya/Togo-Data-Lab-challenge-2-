import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from src.data_loader import get_geojson, get_prefecture_indicators
from src.style_loader import filter_title, inject_styles, sidebar_brand
from src.utils import format_int

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
