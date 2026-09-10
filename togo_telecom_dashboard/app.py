import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    COLORS,
    get_agences,
    get_datacenters,
    get_kpis,
    get_mobile_money,
)
from src.utils import format_int

st.set_page_config(
    page_title="Diagnostic Télécoms & Inclusion Numérique — Togo",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Diagnostic de l'accès aux télécommunications et services numériques — Togo")
st.caption(
    "Cartographie des infrastructures télécoms, des points mobile money et diagnostic "
    "des zones sous-desservies, pour éclairer les priorités d'extension de la connectivité."
)

kpis = get_kpis()

st.markdown("### Chiffres-clés")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Population du Togo (RGPH-5, 2022)", format_int(kpis["population_totale"]))
c2.metric("Agences opérateurs", format_int(kpis["nb_agences"]),
          help=f"Togocom : {kpis['nb_agences_togocom']} · Moov : {kpis['nb_agences_moov']}")
c3.metric("Agents mobile money", format_int(kpis["nb_agents_mm"]))
c4.metric("Datacenters recensés", format_int(kpis["nb_datacenters"]))
c5.metric(
    "Cantons sans agence opérateur",
    f"{kpis['nb_cantons_sans_agence']} / {kpis['nb_cantons']}",
    help="Cantons ne disposant d'aucune agence physique Togocom ou Moov — "
         "ils reposent uniquement sur des agents mobile money indépendants.",
)

st.divider()

left, right = st.columns([2, 1])

with left:
    st.markdown("### Carte nationale des infrastructures")
    st.caption("Agences opérateurs et datacenters — vue d'ensemble (le détail par opérateur "
               "et les agents mobile money sont sur la page *Cartographie*).")

    agences = get_agences()
    dc = get_datacenters()

    map_df = pd.concat(
        [
            agences[["lon", "lat", "operateur", "etab_nom", "prefecture_nom_bdd"]].rename(
                columns={"operateur": "type"}
            ),
            dc.assign(type="Datacenter")[["lon", "lat", "type", "etab_nom", "prefecture_nom_bdd"]],
        ],
        ignore_index=True,
    )

    fig = px.scatter_map(
        map_df,
        lat="lat",
        lon="lon",
        color="type",
        color_discrete_map=COLORS,
        hover_name="etab_nom",
        hover_data={"prefecture_nom_bdd": True, "lat": False, "lon": False, "type": False},
        zoom=6.2,
        center={"lat": 8.6, "lon": 1.0},
        height=520,
    )
    fig.update_layout(
        map_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("### Comment lire ce dashboard")
    st.markdown(
        """
1. ** Cartographie** — répartition spatiale des agences, datacenters et
   agents mobile money, avec filtres région / préfecture / opérateur.
2. ** Mobile money vs population** — adéquation entre densité de points
   mobile money et poids démographique, par préfecture.
3. ** Zones blanches** — cantons sans présence d'agence opérateur,
   classés par priorité d'intervention.
4. ** Recommandations** — synthèse chiffrée et priorisation stratégique.
        """
    )
    st.info(
        "**Limites de données assumées** : le fichier *Agences CANAL+* fourni "
        "est vide (0 ligne) et le fichier *Agences Télécom* est en réalité un "
        "doublon exact de Togocom + Moov — il n'a donc pas été utilisé pour "
        "éviter un double comptage. Aucune donnée officielle de couverture "
        "réseau 2G/3G/4G n'étant disponible en open data pour le Togo, "
        "l'analyse des zones sous-desservies repose sur un **proxy "
        "infrastructure** (présence/absence de points de service), détaillé "
        "sur la page *Zones blanches*.",
        icon="ℹ️",
    )
    st.caption(
        "Sources : jeux de données télécoms fournis pour le challenge · "
        "Population par préfecture — INSEED Togo, RGPH-5 (novembre 2022) · "
        "Limites administratives — geoBoundaries.org (CC BY 4.0)."
    )
