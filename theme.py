"""Speakeasy Ledger theme loader for the Torn Cashflow app.

Usage — add these two lines to the TOP of every page (Home.py and each file in
pages/), right after `st.set_page_config(...)`:

    import theme
    theme.inject_theme()

Base colors and fonts come from .streamlit/config.toml ([theme] /
[[theme.fontFaces]] — self-hosted files under static/fonts/). Fonts are
declared there rather than loaded via a script-injected <link>/@import so
they load once as part of Streamlit's own theme bootstrap, not re-fetched
and re-applied on every page navigation (which caused a visible font flash).
This module only layers the deco borders, KPI brackets, and gold accents on
top via speakeasy.css.
"""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "speakeasy.css"


def inject_theme() -> None:
    """Inject the Speakeasy Ledger CSS. Cheap to call on every page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
