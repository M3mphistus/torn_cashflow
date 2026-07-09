"""Speakeasy Ledger theme loader for the Torn Cashflow app.

Usage — add these two lines to the TOP of every page (app.py and each file in
pages/), right after `st.set_page_config(...)`:

    import theme
    theme.inject_theme()

Base colors come from .streamlit/config.toml ([theme]); this module layers the
art-deco typography, borders and gold accents on top via speakeasy.css.
"""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "speakeasy.css"


def inject_theme() -> None:
    """Inject the Speakeasy Ledger CSS. Cheap to call on every page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
