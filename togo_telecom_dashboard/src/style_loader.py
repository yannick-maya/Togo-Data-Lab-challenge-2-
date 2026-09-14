"""
Centralized design system for the Togo Telecom Dashboard.

``inject_styles()`` loads assets/style.css once per session. The CSS holds
the visual tokens as CSS variables (:root). The Python ``THEME`` below
mirrors those tokens for Plotly figures (charts/maps must not hardcode
hex codes page by page).
"""
from pathlib import Path
import streamlit as st

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_CSS_PATH = _ASSETS_DIR / "style.css"

# Design tokens — miroir Python du :root de style.css (garder en phase).
THEME = {
    "bg_base": "#0E1613",
    "bg_panel": "#16211D",
    "bg_elevated": "#1D2A24",
    "text_primary": "#EDEDE7",
    "text_secondary": "#8FA098",
    "text_faint": "#77887E",
    "accent_primary": "#E8A33D",
    "accent_secondary": "#4FD1C5",
    "danger": "#DD5F52",
    "ok": "#57B98A",
    "warn": "#C58F5C",
    "line": "#24332C",
    "line_strong": "#2E4239",
}

# Fond de carte sombre cohérent avec le thème NOC.
MAP_STYLE = "carto-darkmatter"

# Séquences Plotly réutilisées (régions, ratios, distances, densité).
REGION_COLORS = [
    THEME["accent_secondary"], THEME["accent_primary"], THEME["text_secondary"],
    "#9B7EDE", THEME["danger"],
]
RATE_SCALE = ["#1E3330", "#2E5A50", "#3F8A78", THEME["accent_secondary"]]
DENS_SCALE = ["#24332C", "#5F6E66", "#A9B2A3", THEME["accent_primary"]]
DIST_SCALE = ["#1F2B27", "#8A5A2E", "#D9A441", THEME["accent_primary"]]
DASH_COLOR = THEME["text_secondary"]


def inject_styles():
    """Inject the dashboard CSS once per session (idempotent)."""
    if "_css_injected" not in st.session_state:
        css = _CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        st.session_state["_css_injected"] = True


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
    """Render the control-room brand banner at the top of the sidebar."""
    st.sidebar.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-icon">📡</div>'
        '<div>'
        '<div class="sidebar-brand-title">Togo Télécoms — NOC</div>'
        '<div class="sidebar-brand-sub">Diagnostic &amp; inclusion numérique</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def filter_title(label: str = "Filtres"):
    """Styled title marking the start of the filter area in the sidebar."""
    st.sidebar.markdown(f'<div class="filter-title">{label}</div>', unsafe_allow_html=True)