import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import get_canton_indicators, get_prefecture_indicators
from src.utils import format_int

st.set_page_config(page_title="Recommandations", page_icon="💡", layout="wide")

st.title("💡 Synthèse et recommandations stratégiques")

pref = get_prefecture_indicators()
cantons = get_canton_indicators()

cantons_prioritaires_par_pref = (
    cantons.groupby("prefecture_nom_bdd")["zone_prioritaire"].sum().rename("nb_cantons_prioritaires")
)
pref = pref.merge(cantons_prioritaires_par_pref, left_on="prefecture", right_index=True, how="left")
pref["nb_cantons_prioritaires"] = pref["nb_cantons_prioritaires"].fillna(0)

# Score de priorité simple et transparent : poids démographique x carence en agences,
# pondéré par le nombre de cantons déjà identifiés comme prioritaires dans la préfecture.
pref["score_priorite"] = (
    (pref["population_totale"] / pref["population_totale"].max())
    * (1 - pref["agences_pour_10k_hab"] / pref["agences_pour_10k_hab"].max())
    * (1 + pref["nb_cantons_prioritaires"])
).round(2)

st.markdown("### Préfectures prioritaires pour l'extension de la connectivité")
st.caption(
    "Score combinant poids démographique, faible densité d'agences opérateurs "
    "et nombre de cantons déjà identifiés comme sous-desservis. Un score élevé "
    "signale un fort impact potentiel si des points de service y sont ajoutés."
)

top5 = pref.sort_values("score_priorite", ascending=False).head(5)
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
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.markdown("### Recommandations")

top_pref_names = ", ".join(top5["prefecture"].tolist())
nb_cantons_prioritaires_total = int(cantons["zone_prioritaire"].sum())
nb_cantons_sans_agence = int(cantons["sans_agence_operateur"].sum())

st.markdown(f"""
**1. Prioriser l'implantation de nouvelles agences physiques dans les préfectures à fort score**
({top_pref_names}) — ces zones combinent un poids démographique important, une très
faible densité actuelle d'agences (souvent proche de 0 pour 10 000 habitants) et
plusieurs cantons déjà identifiés comme sous-desservis.

**2. Structurer le réseau d'agents mobile money là où il constitue le seul point de
contact numérique** — {format_int(nb_cantons_sans_agence)} cantons sur {format_int(len(cantons))}
({nb_cantons_sans_agence/len(cantons)*100:.0f} %) n'ont aucune agence opérateur physique et
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

**5. Combler les angles morts de mesure avant la prochaine itération** — aucune
donnée de couverture réseau mobile officielle n'existe en open data pour le Togo,
et les données CANAL+ fournies pour ce challenge sont vides : ces deux limites
méritent d'être signalées aux porteurs du challenge / futurs analystes plutôt que
masquées, car elles conditionnent la fiabilité du diagnostic "zones blanches".
""")

st.markdown("### Table complète des indicateurs par préfecture")
st.dataframe(
    pref[
        ["region", "prefecture", "population_totale", "nb_agences", "nb_agents_mobile_money",
         "agences_pour_10k_hab", "nb_cantons_prioritaires", "score_priorite"]
    ].rename(columns={
        "region": "Région", "prefecture": "Préfecture", "population_totale": "Population",
        "nb_agences": "Nb agences", "nb_agents_mobile_money": "Nb agents MM",
        "agences_pour_10k_hab": "Agences / 10k hab.",
        "nb_cantons_prioritaires": "Cantons prioritaires", "score_priorite": "Score priorité",
    }).sort_values("Score priorité", ascending=False),
    use_container_width=True,
    height=400,
)
