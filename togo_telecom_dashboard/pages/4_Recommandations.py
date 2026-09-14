import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import get_canton_indicators, get_prefecture_indicators
from src.style_loader import card, inject_styles, sidebar_brand
from src.utils import format_int

st.set_page_config(page_title="Recommandations", page_icon="💡", layout="wide")

inject_styles()
sidebar_brand()

st.title("💡 Synthèse et recommandations stratégiques")

with st.spinner("Calcul des scores de priorité…"):
    pref = get_prefecture_indicators()
    cantons = get_canton_indicators()

    cantons_prioritaires_par_pref = (
        cantons.groupby("prefecture_nom_bdd")["zone_prioritaire"].sum().rename("nb_cantons_prioritaires")
    )
    pref = pref.merge(cantons_prioritaires_par_pref, left_on="prefecture", right_index=True, how="left")
    pref["nb_cantons_prioritaires"] = pref["nb_cantons_prioritaires"].fillna(0)

    pref["score_priorite"] = (
        (pref["population_totale"] / pref["population_totale"].max())
        * (1 - pref["agences_pour_10k_hab"] / pref["agences_pour_10k_hab"].max())
        * (1 + pref["nb_cantons_prioritaires"])
    ).round(2)

    top5 = pref.sort_values("score_priorite", ascending=False).head(5)
    nb_cantons_prioritaires_total = int(cantons["zone_prioritaire"].sum())
    nb_cantons_sans_agence = int(cantons["sans_agence_operateur"].sum())
    total_cantons = len(cantons)

# ---------------------------------------------------------------- Executive Summary
st.markdown("#### Résumé exécutif")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        card(
            title="Cantons sans aucune agence",
            value=f"{format_int(nb_cantons_sans_agence)} / {format_int(total_cantons)}",
            subtitle=f"{nb_cantons_sans_agence/total_cantons*100:.0f} % du total",
        ),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        card(
            title="Zones prioritaires identifiées",
            value=format_int(nb_cantons_prioritaires_total),
            subtitle="Sans agence ET peu d'agents mobile money",
            css_class="exec-card-red",
        ),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        card(
            title="Préfecture la plus critique",
            value=top5.iloc[0]["prefecture"],
            subtitle=f"Score de priorité : {top5.iloc[0]['score_priorite']:.2f}",
            css_class="exec-card-amber",
        ),
        unsafe_allow_html=True,
    )

st.divider()

# ------------------------------------------------ Poids démographique de la sous-desserte
st.markdown("#### Poids démographique de la sous-desserte (niveau canton)")
st.caption(
    "Population RGPH-5 (INSEED 2022) rattachée aux cantons, croisée avec la présence "
    "d'infrastructures. Périmètre : les cantons dont la population est publiée "
    "(hors Golfe, Agoè-Nyivé et Danyi, publiés par quartiers/communes)."
)

with st.spinner("Croisement population / desserte…"):
    pop_connue = int(cantons["population_totale"].sum())
    pop_sans_agence = int(cantons.loc[cantons["sans_agence_operateur"], "population_totale"].sum())
    pop_prioritaire = int(cantons.loc[cantons["zone_prioritaire"], "population_totale"].sum())
    nb_cantons_pop = int(cantons["population_totale"].notna().sum())

c1, c2, c3 = st.columns(3)
c1.metric(
    "Population dans un canton sans agence opérateur",
    format_int(pop_sans_agence),
    help="= % de la population canton connue vivant dans un canton sans aucune "
         "agence physique Togocom ou Moov (relais : agents mobile money uniquement).",
)
delta_prior = f"{pop_prioritaire/pop_connue*100:.0f} % de la pop. connue"
c2.metric("Population en zone prioritaire", format_int(pop_prioritaire), delta=delta_prior, delta_color="off")
c3.metric(
    "Population canton couverte",
    f"{format_int(pop_connue)} · {nb_cantons_pop} cantons",
    help="Cantons pour lesquels la population RGPH-5 est publiée et rattachée.",
)

top_peuples = (
    cantons[cantons["sans_agence_operateur"]]
    .sort_values("population_totale", ascending=False)
    .head(10)
)
st.markdown("**Cantons les plus peuplés sans agence opérateur** (le relais mobile money y est la seule présence) :")
st.dataframe(
    top_peuples[
        ["prefecture_nom_bdd", "canton_nom_bdd", "population_totale", "nb_agences", "nb_agents_mobile_money",
         "densite_pop_par_km2"]
    ].rename(columns={
        "prefecture_nom_bdd": "Préfecture", "canton_nom_bdd": "Canton",
        "population_totale": "Population", "nb_agences": "Nb agences",
        "nb_agents_mobile_money": "Nb agents MM", "densite_pop_par_km2": "Hab. / km²",
    }),
    width="stretch",
    height=min(380, 40 + len(top_peuples) * 30),
    column_config={
        "Préfecture": st.column_config.TextColumn(width="medium"),
        "Canton": st.column_config.TextColumn(width="large"),
        "Population": st.column_config.NumberColumn(width="medium", format="%d"),
        "Nb agences": st.column_config.NumberColumn(width="small", format="%d"),
        "Nb agents MM": st.column_config.NumberColumn(width="small", format="%d"),
        "Hab. / km²": st.column_config.NumberColumn(width="small", format="%.0f"),
    },
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------- Top 5 scores
st.markdown("#### Préfectures prioritaires pour l'extension de la connectivité")
st.caption(
    "Score combinant poids démographique, faible densité d'agences opérateurs "
    "et nombre de cantons déjà identifiés comme sous-desservis. Un score élevé "
    "signale un fort impact potentiel si des points de service y sont ajoutés."
)

cols = st.columns(5)
for col, (_, row) in zip(cols, top5.iterrows()):
    with col:
        st.metric(
            row["prefecture"],
            f"score {row['score_priorite']:.2f}",
            help=f"Population : {format_int(row['population_totale'])} · "
                 f"{format_int(row['nb_agences'])} agence(s) · "
                 f"{int(row['nb_cantons_prioritaires'])} canton(s) prioritaire(s)",
        )

fig = px.bar(
    pref.sort_values("score_priorite", ascending=False).head(15),
    x="score_priorite", y="prefecture", orientation="h", color="region",
    labels={"score_priorite": "Score de priorité", "prefecture": ""},
    height=500,
)
fig.update_layout(yaxis=dict(autorange="reversed"), legend=dict(orientation="h", yanchor="bottom", y=1.01))
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------- Recommandations
st.markdown("#### Recommandations")

top_pref_names = ", ".join(top5["prefecture"].tolist())

st.markdown(f"""
**1. Prioriser l'implantation de nouvelles agences physiques dans les préfectures à fort score**
({top_pref_names}) — ces zones combinent un poids démographique important, une très
faible densité actuelle d'agences (souvent proche de 0 pour 10 000 habitants) et
plusieurs cantons déjà identifiés comme sous-desservis.

**2. Structurer le réseau d'agents mobile money là où il constitue le seul point de
contact numérique** — {format_int(nb_cantons_sans_agence)} cantons sur {format_int(total_cantons)}
({nb_cantons_sans_agence/total_cantons*100:.0f} %) n'ont aucune agence opérateur physique et
dépendent uniquement d'agents mobile money indépendants. Un programme de
certification/formation et d'appui logistique pour ces agents renforcerait la fiabilité
du service sans attendre l'implantation d'agences en dur.

**3. Cibler en premier les {format_int(nb_cantons_prioritaires_total)} cantons classés
"zone prioritaire"** (page *Zones blanches*) — ils cumulent l'absence d'agence ET une
faible densité d'agents mobile money : ce sont les zones où le déficit d'accès est le
plus complet.

**4. Décentraliser progressivement les capacités data hors de Lomé** — les 3
datacenters recensés sont tous concentrés dans la région du Golfe (Lomé). Une
réflexion sur un point de présence régional (Kara ou Sokodé, pôles secondaires
par leur population) réduirait la dépendance à un seul point de défaillance
géographique.

**5. Poursuivre l'enrichissement des données hors BDD et combler les angles morts
de mesure** — la couverture réseau mobile officielle n'existe toujours pas en open
data pour le Togo, et le fichier *Agences CANAL+* du jeu de données était vide
(les points de vente réels ont été reconstitués depuis canalbox.tg et OpenStreetMap,
mais cette couche reste partielle). Ces limites méritent d'être signalées aux
porteurs du challenge / futurs analystes plutôt que masquées, car elles
conditionnent la fiabilité du diagnostic "zones blanches".
""")

st.divider()

# ---------------------------------------------------------------- Tableau complet
st.markdown("#### Table complète des indicateurs par préfecture")

df_table = pref[
    ["region", "prefecture", "population_totale", "nb_agences", "nb_agents_mobile_money",
     "agences_pour_10k_hab", "nb_cantons_prioritaires", "score_priorite"]
].rename(columns={
    "region": "Région", "prefecture": "Préfecture", "population_totale": "Population",
    "nb_agences": "Nb agences", "nb_agents_mobile_money": "Nb agents MM",
    "agences_pour_10k_hab": "Agences / 10k hab.",
    "nb_cantons_prioritaires": "Cantons prioritaires", "score_priorite": "Score priorité",
}).sort_values("Score priorité", ascending=False)

st.dataframe(
    df_table,
    width="stretch",
    height=400,
    column_config={
        "Région": st.column_config.TextColumn(width="small"),
        "Préfecture": st.column_config.TextColumn(width="medium"),
        "Population": st.column_config.NumberColumn(width="medium", format="%d"),
        "Nb agences": st.column_config.NumberColumn(width="small", format="%d"),
        "Nb agents MM": st.column_config.NumberColumn(width="small", format="%d"),
        "Agences / 10k hab.": st.column_config.NumberColumn(width="medium", format="%.2f"),
        "Cantons prioritaires": st.column_config.NumberColumn(width="small", format="%d"),
        "Score priorité": st.column_config.NumberColumn(width="small", format="%.2f"),
    },
    hide_index=True,
)
