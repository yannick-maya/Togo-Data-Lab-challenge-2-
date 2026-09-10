"""
Centralized CSS injection for the Togo Telecom Dashboard.
Call inject_styles() at the top of every page (after set_page_config)
to load assets/style.css exactly once per Streamlit session.
"""
from pathlib import Path
import streamlit as st

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_CSS_PATH = _ASSETS_DIR / "style.css"


def inject_styles():
    """Inject the dashboard CSS once per session (idempotent)."""
    if "_css_injected" not in st.session_state:
        css = _CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        st.session_state["_css_injected"] = True


def card(title: str, value: str, subtitle: str = "", css_class: str = ""):
    """Render a styled executive-summary card as HTML."""
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
    """Render the dashboard brand banner at the top of the sidebar."""
    st.sidebar.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-icon">📡</div>'
        '<div>'
        '<div class="sidebar-brand-title">Togo Télécoms</div>'
        '<div class="sidebar-brand-sub">Diagnostic &amp; inclusion numérique</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def filter_title(label: str = "Filtres"):
    """Styled title marking the start of the filter area in the sidebar."""
    st.sidebar.markdown(f'<div class="filter-title">{label}</div>', unsafe_allow_html=True)
