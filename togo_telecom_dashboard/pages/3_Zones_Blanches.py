import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from src.data_loader import COLORS, get_canton_indicators
from src.style_loader import filter_title, inject_styles, sidebar_brand
from src.utils import format_int

st.set_page_config(page_title="Zones blanches", page_icon="📡", layout="wide")

inject_styles()
sidebar_brand()

st.title("📡 Identification des zones sous-desservies")

st.warning(
    "**Note méthodologique** — Aucune donnée officielle de couverture réseau "
    "2G/3G/4G n'est disponible en open data pour le Togo (contrairement, par "
    "exemple, à l'ARCEP en France). Cette page utilise donc un **proxy "
    "infrastructure** : un canton est considéré comme mal desservi lorsqu'il "
    "ne dispose d'**aucune agence physique Togocom ou Moov**, et classé "
    "**zone prioritaire** lorsqu'il cumule cette absence avec un nombre "
    "d'agents mobile money parmi les plus faibles du pays (quartile "
    "inférieur). Ce n'est pas une mesure de couverture radio réelle.",
    icon="⚠️",
)

with st.spinner("Chargement des indicateurs canton…"):
    cantons = get_canton_indicators()

regions = sorted(cantons["region_nom_bdd"].unique())
filter_title()
region_sel = st.sidebar.multiselect("Région", regions, default=regions)
cantons_f = cantons[cantons["region_nom_bdd"].isin(region_sel)].copy()

if cantons_f.empty:
    st.warning("Aucun canton ne correspond à la région sélectionnée. Modifiez le filtre dans la barre latérale.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Cantons analysés", format_int(len(cantons_f)))
c2.metric(
    "Sans agence opérateur",
    f"{int(cantons_f['sans_agence_operateur'].sum())} "
    f"({cantons_f['sans_agence_operateur'].mean()*100:.0f} %)",
)
c3.metric("Classés zone prioritaire", format_int(int(cantons_f["zone_prioritaire"].sum())))

st.divider()

st.markdown("#### Carte des cantons par niveau de desserte")
cantons_f["statut"] = cantons_f["zone_prioritaire"].map(
    {True: "Zone prioritaire", False: "Desserte correcte"}
)
cantons_f.loc[
    (~cantons_f["zone_prioritaire"]) & (cantons_f["sans_agence_operateur"]), "statut"
] = "Sans agence (hors priorité haute)"

with st.spinner("Construction de la carte…"):
    fig = px.scatter_map(
        cantons_f,
        lat="lat", lon="lon",
        color="statut",
        color_discrete_map={
            "Zone prioritaire": COLORS["Zone prioritaire"],
            "Sans agence (hors priorité haute)": "#F4A259",
            "Desserte correcte": COLORS["Bonne desserte"],
        },
        size="nb_agents_mobile_money",
        size_max=22,
        hover_name="canton_nom_bdd",
        hover_data={
            "prefecture_nom_bdd": True, "nb_agences": True, "nb_agents_mobile_money": True,
            "lat": False, "lon": False, "statut": False,
        },
        zoom=6.2, center={"lat": 8.6, "lon": 1.0}, height=600,
    )
    fig.update_layout(
        map_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------- Tableau Top 20
st.markdown("#### Top 20 cantons prioritaires (sans agence, peu d'agents mobile money)")
top = (
    cantons_f[cantons_f["zone_prioritaire"]]
    .sort_values("nb_agents_mobile_money")
    .head(20)
)

if top.empty:
    st.info("Aucun canton classé « zone prioritaire » dans la région sélectionnée.")
else:
    st.dataframe(
        top[
            ["region_nom_bdd", "prefecture_nom_bdd", "canton_nom_bdd", "nb_agences", "nb_agents_mobile_money"]
        ].rename(columns={
            "region_nom_bdd": "Région", "prefecture_nom_bdd": "Préfecture", "canton_nom_bdd": "Canton",
            "nb_agences": "Nb agences", "nb_agents_mobile_money": "Nb agents MM",
        }),
        width="stretch",
        height=min(420, 40 + len(top) * 30),
        column_config={
            "Région": st.column_config.TextColumn(width="small"),
            "Préfecture": st.column_config.TextColumn(width="medium"),
            "Canton": st.column_config.TextColumn(width="medium"),
            "Nb agences": st.column_config.NumberColumn(width="small", format="%d"),
            "Nb agents MM": st.column_config.NumberColumn(width="small", format="%d"),
        },
        hide_index=True,
    )

# ---------------------------------------------------------------- Bar chart
st.markdown("#### Répartition des préfectures par nombre de cantons prioritaires")
by_pref = (
    cantons_f.groupby(["region_nom_bdd", "prefecture_nom_bdd"])["zone_prioritaire"]
    .sum()
    .reset_index()
    .sort_values("zone_prioritaire", ascending=False)
    .head(15)
)
fig_bar = px.bar(
    by_pref, x="zone_prioritaire", y="prefecture_nom_bdd", color="region_nom_bdd",
    orientation="h",
    labels={"zone_prioritaire": "Nb de cantons prioritaires", "prefecture_nom_bdd": ""},
    height=max(350, len(by_pref) * 30),
)
fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.01))
st.plotly_chart(fig_bar, width="stretch")
