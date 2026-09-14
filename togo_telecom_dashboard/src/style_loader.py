"""
Centralized design system for the Togo Telecom Dashboard.

``inject_styles()`` loads assets/style.css once per session. The CSS holds
the visual tokens as CSS variables (:root). The Python ``THEME`` below
mirrors those tokens for Plotly figures (charts/maps must not hardcode
hex codes page by page).
"""
from pathlib import Path
import streamlit as st

from src.components.icons import svg

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_CSS_PATH = _ASSETS_DIR / "style.css"

# Favicon de l'application (silhouette de poste de contrôle, sans émoji).
FAVICON = str(_ASSETS_DIR / "favicon.svg")

# Design tokens — miroir Python du :root de style.css (garder en phase).
# Variante claire : contenu et rail de navigation clairs et lisibles.
THEME = {
    "bg_base": "#F6F8F7",
    "bg_panel": "#F1F5F2",
    "bg_elevated": "#FFFFFF",
    "text_primary": "#1B2420",
    "text_secondary": "#56655C",
    "text_faint": "#7A8A81",
    "accent_primary": "#E8A33D",
    "accent_ink": "#A16100",
    "accent_secondary": "#0E9A8E",
    "danger": "#C24538",
    "ok": "#2E8B67",
    "warn": "#A8752B",
    "line": "#D9E1DA",
    "line_strong": "#C3CFC6",
}

# Fond de carte clair cohérent avec la variante claire du thème.
MAP_STYLE = "carto-positron"

# Séquences Plotly réutilisées (régions, ratios, distances, densité).
# 6e/7e couleurs palettes existantes, ajoutées pour distinguer la 6e
# division administrative « Grand Lomé » sans couleur hors tokens.
REGION_COLORS = [
    THEME["accent_secondary"], "#B26B10", THEME["text_secondary"],
    "#7456B4", THEME["danger"], THEME["ok"], THEME["warn"],
]
RATE_SCALE = ["#CBE6DE", "#79C2B1", "#3FA08D", THEME["accent_secondary"]]
DENS_SCALE = ["#E3EAE2", "#B7C4B4", "#D9A86A", "#B26B10"]
DIST_SCALE = ["#E3EAE2", "#C19B5E", "#C07A1D", "#8A5A00"]
DASH_COLOR = THEME["text_secondary"]

# Police Plotly alignée sur la feuille de style.
_FONT_STACK = "IBM Plex Sans, Inter, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"


def style_figure(fig):
    """Force un rendu Plotly clair et lisible, quel que soit le thème Streamlit.

    Appliquer après les update_layout() des figures (cartes comprises) pour
    garantir un fond blanc, un texte sombre et des quadrillages visibles.
    """
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT_STACK, color=THEME["text_primary"], size=12),
    )
    fig.update_xaxes(
        gridcolor="#E7EDE9", zerolinecolor=THEME["line"], linecolor=THEME["line"],
        title_font=dict(color=THEME["text_secondary"]),
    )
    fig.update_yaxes(
        gridcolor="#E7EDE9", zerolinecolor=THEME["line"], linecolor=THEME["line"],
        title_font=dict(color=THEME["text_secondary"]),
    )
    fig.update_annotations(font=dict(color=THEME["text_primary"]))
    return fig


_region_colors_cache = None


def region_color_map() -> dict:
    """Une couleur par région, stable sur toutes les pages (ordre alphabétique).

    Permet de comparer les graphiques régionaux d'une page à l'autre : les
    mêmes teintes de palette tracent les mêmes régions partout.
    """
    global _region_colors_cache
    if _region_colors_cache is None:
        from src.data_loader import get_prefecture_indicators

        pref = get_prefecture_indicators()
        regs = sorted(pref["region"].dropna().unique())
        _region_colors_cache = {
            r: REGION_COLORS[i % len(REGION_COLORS)] for i, r in enumerate(regs)
        }
    return _region_colors_cache


def page_header(icon_key: str, title: str, caption: str = "") -> str:
    """En-tête de page : icône SVG ligne fine + titre + légende (pas d'émoji)."""
    cap = f'<div class="page-header-caption">{caption}</div>' if caption else ""
    return (
        '<div class="page-header">'
        f'<div class="page-header-icon">{svg(icon_key, 22)}</div>'
        f'<div class="page-header-text"><div class="page-header-title">{title}</div>{cap}</div>'
        '</div>'
    )


def inject_styles():
    """Inject the dashboard CSS on every script run.

    Nécessaire en multipage : la balise <style> émise par une page est retirée
    du DOM lors de la navigation ; l'injecter à chaque exécution évite de
    laisser une page sans style (et un rail qui « redevient » clair).
    """
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def hero(label: str, value: str, note: str = "", unit: str = "", tone: str = "accent",
         live: bool = True) -> str:
    """Render a control-room instrument readout (the ONE strong signal per screen).

    tone: "accent" (amber), "danger" (deficit) or "cyan" (network).
    Use monospace numbers only — it is an instrument display, not decoration.
    """
    tone_cls = {"accent": "", "danger": " tone-danger", "cyan": " tone-cyan"}.get(tone, "")
    live_html = '<span class="live-dot"></span>' if live else ""
    unit_html = f'<span class="hero-unit">{unit}</span>' if unit else ""
    note_html = f'<div class="hero-note">{note}</div>' if note else ""
    return (
        f'<div class="hero-meter{tone_cls}">'
        f'<div class="hero-label">{live_html}{label}</div>'
        f'<div class="hero-value">{value}{unit_html}</div>'
        f"{note_html}"
        f'</div>'
    )


def card(title: str, value: str, subtitle: str = "", css_class: str = ""):
    """Render a panel-style summary card as HTML (executive summary)."""
    cls = f"exec-card {css_class}".strip()
    subtitle_html = f'<div class="exec-label">{subtitle}</div>' if subtitle else ""
    return (
        f'<div class="{cls}">'
        f'<div class="exec-label">{title}</div>'
        f'<div class="exec-value">{value}</div>'
        f"{subtitle_html}"
        f'</div>'
    )


def sidebar_brand():
    """Render the control-room brand banner at the top of the sidebar.

    Affiche d'abord le logo partenaire (décoration, base64) puis la marque du
    poste de contrôle. Appelée par chaque page : présent sur toute la navigation.
    """
    sidebar_logo()
    st.sidebar.markdown(
        '<div class="sidebar-brand">'
        f'<div class="sidebar-brand-icon">{svg("radar", 24)}</div>'
        '<div>'
        '<div class="sidebar-brand-title">Togo Télécoms — NOC</div>'
        '<div class="sidebar-brand-sub">Diagnostic &amp; inclusion numérique</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def sidebar_logo():
    """Logo partenaire en tête du rail — données image embarquées (base64)."""
    logo_path = _ASSETS_DIR / "logo.png"
    if not logo_path.exists():
        return
    import base64

    b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    st.sidebar.markdown(
        f'<div class="sidebar-logo"><img alt="Logo" src="data:image/png;base64,{b64}" /></div>',
        unsafe_allow_html=True,
    )