"""Onglet Scatter : nuage de points interactif."""

import pandas as pd
import streamlit as st

from moneyballer.analysis import stat_columns
from moneyballer.charts.scatter import draw_scatter
from moneyballer.config import SCORE_COL, STATS_COLS


def render(pop: pd.DataFrame, players: list[dict], pct_mode: bool) -> None:
    cols = [c for c in stat_columns(pop) if c != "Mins"]
    x_default = cols.index(STATS_COLS[0]) if STATS_COLS[0] in cols else 0
    y_default = cols.index(SCORE_COL) if SCORE_COL in cols else min(1, len(cols) - 1)

    c_x, c_y = st.columns(2)
    with c_x:
        x_col = st.selectbox("Axe X", options=cols, index=x_default, key="scatter_x")
    with c_y:
        y_col = st.selectbox("Axe Y", options=cols, index=y_default, key="scatter_y")

    c_out, c_k = st.columns([1, 2])
    with c_out:
        show_outliers = st.checkbox(
            "🔍 Détecter les outliers", value=False, key="show_outliers"
        )
    with c_k:
        outlier_k = st.slider(
            "Sensibilité (× IQR)",
            min_value=0.5,
            max_value=3.0,
            value=1.5,
            step=0.1,
            key="outlier_k",
            disabled=not show_outliers,
            help="1.5 = outliers classiques · 3.0 = extrêmes seulement",
        )

    st.plotly_chart(
        draw_scatter(pop, x_col, y_col, players, pct_mode, show_outliers, outlier_k)
    )
