"""
Barre de filtres horizontale partagée (Tâche 3).

Les filtres globaux (région, préfecture, opérateur, statut…) vivent dans un
bandeau en tête du contenu principal — jamais dans la sidebar, réservée à la
navigation. Les sélections persistent entre les pages via ``st.session_state``
(clés préfixées ``filters_``).

Utilisation :
    f = filter_bar(region=True, prefecture=True, operateur=True, layers=True)
    region_sel = f.region
    if f.layers["agences"]: ...
"""
import streamlit as st

from src.components.icons import svg
from src.data_loader import get_agences, get_prefecture_indicators

# Clés de session_state persistantes (préfixe commun pour le reset global).
_KEYS_REGION = "filters_region"
_KEYS_PREFECTURE = "filters_prefecture"
_KEYS_OPERATEUR = "filters_operateur"
_KEYS_STATUT = "filters_statut"
_KEYS_COLOR_BY = "filters_color_by"
_LAYER_KEYS = {
    "agences": ("filters_show_agences", True),
    "dc": ("filters_show_dc", True),
    "mm": ("filters_show_mm", True),
    "canal": ("filters_show_canal", False),
}

_FILTER_KEYS = [
    _KEYS_REGION, _KEYS_PREFECTURE, _KEYS_OPERATEUR, _KEYS_STATUT,
    _KEYS_COLOR_BY, *[k for k, _ in _LAYER_KEYS.values()],
]

STATUT_OPTIONS = [
    "Zone prioritaire",
    "Sans agence (hors priorité haute)",
    "Desserte correcte",
]
COLOR_BY_OPTIONS = [
    "Statut de desserte",
    "Densité de population (hab./km²)",
    "Distance à la plus proche agence",
]


class FilterState:
    """État courant de la barre de filtres (lecture seule pour les pages)."""

    def __init__(self, region, prefecture, operateur, statut, color_by, layers):
        self.region = list(region or [])
        self.prefecture = list(prefecture or [])
        self.operateur = list(operateur or [])
        self.statut = list(statut or [])
        self.color_by = color_by
        self.layers = dict(layers)


def _trim(key: str, options):
    """Retire de la sélection mémorisée les valeurs devenues indisponibles."""
    if key not in st.session_state:
        return
    kept = [v for v in st.session_state[key] if v in options]
    st.session_state[key] = kept


def _prime_stored():
    for key, default in _LAYER_KEYS.values():
        st.session_state.setdefault(key, default)
    st.session_state.setdefault(_KEYS_COLOR_BY, COLOR_BY_OPTIONS[0])


def _reset_handler():
    for key in _FILTER_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


def filter_bar(
    region: bool = True,
    prefecture: bool = True,
    operateur: bool = False,
    statut: bool = False,
    color_by: bool = False,
    layers: bool = False,
    region_options=None,
    prefecture_options=None,
):
    """Affiche la barre de filtres et renvoie un objet ``FilterState``.

    ``region_options`` / ``prefecture_options`` : callables optionnels qui
    renvoient les valeurs proposées par la page courante (par exemple basées
    sur le jeu de données de la page). Sans valeur, la liste canonique est
    celle d'``indicateurs_prefecture.csv``.
    """
    pref = get_prefecture_indicators()
    regs = region_options() if region_options is not None else sorted(pref["region"].dropna().unique())

    _prime_stored()
    _trim(_KEYS_REGION, regs)

    st.markdown('<span class="filter-bar-anchor"></span>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            f'<div class="filter-bar-title">{svg("funnel", 14)}</div>',
            unsafe_allow_html=True,
        )

        # --- Ligne 1 : sélecteurs principaux ---------------------------------
        row1 = [("region", 1.3)]
        if prefecture:
            row1.append(("prefecture", 1.7))
        if operateur:
            row1.append(("operateur", 1.0))
        if statut:
            row1.append(("statut", 1.4))

        region_sel = []
        prefecture_sel = []
        operateur_sel = []
        statut_sel = []

        row1_cols = st.columns([w for _, w in row1], gap="medium")
        for (kind, _w), col in zip(row1, row1_cols):
            with col:
                if kind == "region":
                    st.session_state.setdefault(_KEYS_REGION, regs)
                    region_sel = st.multiselect("Région", regs, key=_KEYS_REGION)
                elif kind == "prefecture":
                    if prefecture_options is not None:
                        avail = sorted(prefecture_options(region_sel) or [])
                    else:
                        avail = sorted(
                            pref.loc[pref["region"].isin(region_sel), "prefecture"].dropna().unique()
                        )
                    _trim(_KEYS_PREFECTURE, avail)
                    st.session_state.setdefault(_KEYS_PREFECTURE, avail)
                    prefecture_sel = st.multiselect("Préfecture", avail, key=_KEYS_PREFECTURE)
                elif kind == "operateur":
                    ops = sorted(get_agences()["operateur"].dropna().unique())
                    _trim(_KEYS_OPERATEUR, ops)
                    st.session_state.setdefault(_KEYS_OPERATEUR, ops)
                    operateur_sel = st.multiselect("Opérateur (agences)", ops, key=_KEYS_OPERATEUR)
                elif kind == "statut":
                    _trim(_KEYS_STATUT, STATUT_OPTIONS)
                    st.session_state.setdefault(_KEYS_STATUT, STATUT_OPTIONS)
                    statut_sel = st.multiselect("Statut de desserte", STATUT_OPTIONS, key=_KEYS_STATUT)

        reset_cols_needed = region or prefecture or operateur or statut
        if reset_cols_needed:
            with row1_cols[-1]:
                st.caption("")
                if st.button("Réinitialiser", key="_filters_reset", use_container_width=True):
                    _reset_handler()

        # --- Ligne 2 : coloration des cantons + couches ----------------------
        if layers:
            layer_labels = {
                "agences": "Agences",
                "dc": "Datacenters",
                "mm": "Mobile money",
                "canal": "CANAL+ (externe)",
            }
            if color_by:
                # coloration et couches sur la même ligne : couches à droite
                lay_cols = st.columns([1.0, 0.72, 0.72, 0.72, 0.72], gap="medium")
                with lay_cols[0]:
                    color_by_sel = st.selectbox(
                        "Coloration des cantons", COLOR_BY_OPTIONS, key=_KEYS_COLOR_BY
                    )
                for (name, (key, _default)), col in zip(_LAYER_KEYS.items(), lay_cols[1:]):
                    with col:
                        st.checkbox(layer_labels[name], key=key)
            else:
                lay_cols = st.columns([0.72, 0.72, 0.72, 0.72], gap="medium")
                for (name, (key, _default)), col in zip(_LAYER_KEYS.items(), lay_cols):
                    with col:
                        st.checkbox(layer_labels[name], key=key)
        elif color_by:
            ccol = st.columns([1], gap="medium")
            with ccol[0]:
                color_by_sel = st.selectbox(
                    "Coloration des cantons", COLOR_BY_OPTIONS, key=_KEYS_COLOR_BY
                )

    if color_by:
        color_by_value = st.session_state.get(_KEYS_COLOR_BY, COLOR_BY_OPTIONS[0])
    else:
        color_by_value = None

    return FilterState(
        region=region_sel,
        prefecture=prefecture_sel,
        operateur=operateur_sel,
        statut=statut_sel,
        color_by=color_by_value,
        layers={name: st.session_state.get(key, default)
                for name, (key, default) in _LAYER_KEYS.items()},
    )