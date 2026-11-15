"""Feuille de style globale."""

import streamlit as st

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;600;700&family=Barlow:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Barlow', sans-serif; background-color: #0f0f13; color: #e0e0e0; }
    .stApp { background-color: #0f0f13; }
    h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif; letter-spacing: 0.05em; text-transform: uppercase; }
    section[data-testid="stSidebar"] { background-color: #16161e; border-right: 1px solid #2a2a3a; }
    div[data-testid="stSidebar"] button { padding: 2px 2px !important; font-size: 11px !important; min-height: 26px !important; line-height: 1.1 !important; }
    .metric-card { background: linear-gradient(135deg, #1a1a28 0%, #16161e 100%); border: 1px solid #2a2a3a; border-radius: 8px; padding: 16px; margin-bottom: 8px; }
    .metric-label { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: #888; margin-bottom: 4px; }
    .metric-value { font-family: 'Barlow Condensed', sans-serif; font-size: 24px; font-weight: 700; color: #ffffff; }
    .player-tag { display: inline-block; padding: 4px 10px; border-radius: 3px; font-family: 'Barlow Condensed', sans-serif; font-size: 13px; font-weight: 600; letter-spacing: 0.05em; margin: 2px; }
    .section-title { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: #555; border-bottom: 1px solid #2a2a3a; padding-bottom: 6px; margin-bottom: 12px; margin-top: 20px; }
    .card-title { font-family: 'Barlow Condensed', sans-serif; font-size: 20px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #ffffff; }
    .radar-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 4px 0 12px; font-size: 13px; color: #e0e0e0; }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .legend-line { display: inline-block; width: 22px; }
</style>
"""


def inject_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
