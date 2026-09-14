import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

# Point d'entrée : la navigation Streamlit (st.navigation) remplace le
# multipage classique afin de contrôler l'ordre et les libellés du menu.
# L'entrée n'est plus affichée comme « Application » mais comme « Accueil ».

PAGES = [
    st.Page("pages/0_Accueil.py", title="Accueil", default=True),
    st.Page("pages/1_Cartographie_Infrastructures.py", title="Cartographie des infrastructures"),
    st.Page("pages/2_Mobile_Money_vs_Population.py", title="Mobile Money vs Population"),
    st.Page("pages/3_Zones_Blanches.py", title="Zones blanches"),
    st.Page("pages/4_Recommandations.py", title="Recommandations"),
]

pg = st.navigation(PAGES)
pg.run()