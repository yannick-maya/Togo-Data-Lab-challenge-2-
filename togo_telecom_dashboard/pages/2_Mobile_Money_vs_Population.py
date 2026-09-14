import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.express as px
import streamlit as st

from src.components.filter_bar import filter_bar
from src.data_loader import get_geojson, get_prefecture_indicators
from src.style_loader import FAVICON, MAP_STYLE, RATE_SCALE, REGION_COLORS, THEME, hero, inject_styles, page_header, region_color_map, sidebar_brand, style_figure
from src.utils import format_int, gini_coefficient, lorenz_curve

st.set_page_config(page_title="Mobile money vs population", page_icon=FAVICON, layout="wide")

inject_styles()
sidebar_brand()

st.markdown(
    page_header(
        "wallet",
        "Couverture mobile money et adéquation avec la population",
        "Les points mobile money sont-ils répartis proportionnellement à la population, "
        "ou certaines préfectures très peuplées restent-elles sous-équipées ?",
    ),
    unsafe_allow_html=True,
)

with st.spinner("Chargement des indicateurs par préfecture…"):
    pref = get_prefecture_indicators()
    geo = get_geojson()

filtres = filter_bar(region=True, prefecture=False)
region_sel = filtres.region
pref_f = pref[pref["region"].isin(region_sel)].copy()

if pref_f.empty:
    st.warning("Aucune préfecture ne correspond à la région sélectionnée. Modifiez le filtre dans le bandeau de filtres.")
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
        color_continuous_scale=RATE_SCALE,
        map_style=MAP_STYLE,
        zoom=6.2,
        center={"lat": 8.6, "lon": 1.0},
        opacity=0.8,
        height=560,
        hover_name="prefecture",
        hover_data={"population_totale": True, "nb_agents_mobile_money": True, "polygon_key": False},
        labels={"agents_mm_pour_10k_hab": "Agents / 10k hab."},
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    style_figure(fig_map)
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
        color_discrete_sequence=REGION_COLORS,
        height=max(400, len(ranked) * 28),
        labels={"agents_mm_pour_10k_hab": "Agents mobile money / 10 000 hab.", "prefecture": ""},
    )
    fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.01))
    style_figure(fig_bar)
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
        color_discrete_sequence=REGION_COLORS,
        size="population_totale",
        hover_name="prefecture",
        height=max(400, len(pref_f) * 32),
        labels={"population_totale": "Population (2022)", "nb_agents_mobile_money": "Agents mobile money"},
    )
    xmax = pref_f["population_totale"].max()
    fig_sc.add_shape(
        type="line", x0=0, y0=0, x1=xmax, y1=xmax * moyenne_nationale,
        line=dict(dash="dot", color=THEME["text_secondary"]),
    )
    coef = np.polyfit(pref_f["population_totale"], pref_f["nb_agents_mobile_money"], 1)
    resid = np.abs(
        pref_f["nb_agents_mobile_money"] - np.polyval(coef, pref_f["population_totale"])
    )
    atypiques = pref_f.assign(_resid=resid).nlargest(5, "_resid")
    lbl = px.scatter(
        atypiques, x="population_totale", y="nb_agents_mobile_money", text="prefecture",
    ).data[0]
    lbl.marker.opacity = 0
    lbl.showlegend = False
    lbl.hovertemplate = None
    lbl.textfont = dict(size=11, color=THEME["accent_ink"])
    lbl.textposition = "top center"
    fig_sc.add_trace(lbl)
    style_figure(fig_sc)
    st.plotly_chart(fig_sc, width="stretch")

st.divider()

# ---------------------------------------------------------------- Vue régionale
st.markdown("#### Population, agents mobile money et agences par région")
st.caption(
    "Tri par population décroissante, mêmes couleurs par région que sur la page "
    "*Cartographie* : une région se lit au même endroit d'une page à l'autre."
)

reg_stat = pref_f.groupby("region")[["population_totale", "nb_agents_mobile_money", "nb_agences"]].sum()
pop_ord = reg_stat.sort_values("population_totale", ascending=False)
mm_ord = reg_stat.sort_values("nb_agents_mobile_money", ascending=False)
region_pal = region_color_map()

col_pop, col_mm = st.columns([1, 1], gap="medium")

with col_pop:
    st.markdown("##### Population par région")
    fig_pop = px.bar(
        x=pop_ord["population_totale"],
        y=pop_ord.index,
        orientation="h",
        color=pop_ord.index,
        color_discrete_map=region_pal,
        labels={"x": "Population (2022)", "y": ""},
        height=max(260, 60 + 40 * len(pop_ord)),
    )
    fig_pop.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    style_figure(fig_pop)
    st.plotly_chart(fig_pop, width="stretch")

with col_mm:
    st.markdown("##### Agents mobile money par région")
    fig_mm = px.bar(
        x=mm_ord["nb_agents_mobile_money"],
        y=mm_ord.index,
        orientation="h",
        color=mm_ord.index,
        color_discrete_map=region_pal,
        labels={"x": "Nombre d'agents mobile money", "y": ""},
        height=max(260, 60 + 40 * len(mm_ord)),
    )
    fig_mm.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    style_figure(fig_mm)
    st.plotly_chart(fig_mm, width="stretch")

st.divider()

# ---------------------------------------------------------------- Compensations
st.markdown("#### Agences vs agents mobile money : où les agents compensent l'absence d'agences")
st.caption(
    "Pour les 10 préfectures les plus peuplées, densité d'agences opérateurs et d'agents "
    "mobile money (pour 10 000 habitants). Quand la barre des agents est nettement plus "
    "longue que celle des agences, le réseau d'agents compense l'absence d'infrastructure "
    "physique — une zone de vigilance pour la qualité de service."
)
top_bal = pref_f.sort_values("population_totale", ascending=False).head(10)
bal_melt = (
    top_bal[["prefecture", "agences_pour_10k_hab", "agents_mm_pour_10k_hab"]]
    .melt(id_vars="prefecture", var_name="indicateur", value_name="ratio")
)
bal_melt["indicateur"] = bal_melt["indicateur"].map({
    "agences_pour_10k_hab": "Agences / 10k hab.",
    "agents_mm_pour_10k_hab": "Agents MM / 10k hab.",
})
fig_bal = px.bar(
    bal_melt,
    x="ratio", y="prefecture", color="indicateur", orientation="h", barmode="group",
    color_discrete_map={
        "Agences / 10k hab.": THEME["accent_primary"],
        "Agents MM / 10k hab.": THEME["accent_secondary"],
    },
    labels={"ratio": "Pour 10 000 habitants", "prefecture": ""},
    height=max(360, 40 + 30 * len(top_bal)),
)
fig_bal.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    margin=dict(l=0, r=0, t=10, b=0),
)
style_figure(fig_bal)
st.plotly_chart(fig_bal, width="stretch")

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

col_gini, col_rest = st.columns([1, 2], gap="medium")
with col_gini:
    st.markdown(
        hero(
            label="Gini — agences opérateurs (vs population)",
            value=f"{gini_agences:.3f}",
            tone="accent",
            note="0 = proportionnel à la population — 1 = totalement concentré",
        ),
        unsafe_allow_html=True,
    )
with col_rest:
    n2, n3 = st.columns(2)
    n2.metric("Gini — agents mobile money", f"{gini_mm:.3f}",
              help="0 = proportionnel à la population — 1 = totalement concentré")
    n3.metric(
        "Interprétation",
        "Très inégal" if max(gini_agences, gini_mm) > 0.5 else "Modérément inégal",
        delta="agences ≫ mobile money" if gini_agences > gini_mm else "mobile money ≫ agences",
        delta_color="off",
    )

if p_pts_a is not None:
    fig_lorenz = px.line(x=[0, 1], y=[0, 1], labels={"x": "Part cumulée de la population", "y": "Part cumulée de l'équipement"})
    fig_lorenz.data[0].name = "Répartition équitable (bissectrice)"
    fig_lorenz.add_trace(
        px.line(x=np.concatenate([[0], p_pts_a.to_numpy()]), y=np.concatenate([[0], e_pts_a.to_numpy()])).data[0]
    )
    fig_lorenz.data[1].name = "Agences opérateurs"
    fig_lorenz.add_trace(
        px.line(x=np.concatenate([[0], p_pts_m.to_numpy()]), y=np.concatenate([[0], e_pts_m.to_numpy()])).data[0]
    )
    fig_lorenz.data[2].name = "Agents mobile money"
    fig_lorenz.update_traces(
        line=dict(width=1.5, color=THEME["text_secondary"], dash="dot"),
        selector=dict(name="Répartition équitable (bissectrice)"),
    )
    fig_lorenz.update_traces(
        line=dict(width=3, color=THEME["accent_primary"]),
        selector=dict(name="Agences opérateurs"),
    )
    fig_lorenz.update_traces(
        line=dict(width=3, color=THEME["accent_secondary"]),
        selector=dict(name="Agents mobile money"),
    )
    fig_lorenz.update_traces(
        line=dict(width=3, color=THEME["accent_primary"]),
        selector=dict(name="Agences opérateurs"),
    )
    fig_lorenz.update_traces(
        line=dict(width=3, color=THEME["accent_secondary"]),
        selector=dict(name="Agents mobile money"),
    )
    fig_lorenz.update_layout(
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        xaxis=dict(range=[0, 1.02]), yaxis=dict(range=[0, 1.02]),
        showlegend=True,
    )
    style_figure(fig_lorenz)
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
