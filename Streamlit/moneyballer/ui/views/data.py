"""Vue Data : radar, scatter et tableau sur la population filtrée."""

import pandas as pd
import streamlit as st

from moneyballer.config import SCORE_COL, STATS_COLS
from moneyballer.ui.views import radar, scatter, table

CHART_RADAR = "📡 Radar"
CHART_SCATTER = "📊 Scatter"
CHART_TABLE = "📋 Tableau"


def render(pop: pd.DataFrame, selected_names: list[str]) -> None:
    _info_bar(pop)

    missing = [c for c in STATS_COLS if c not in pop.columns]
    if missing:
        st.error(f"Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    pct_mode = st.checkbox(
        "📐 Mode percentile (recalculé sur la population filtrée)",
        value=False,
        key="pct_mode",
    )
    players = _collect_players(pop, selected_names)

    chart_type = st.radio(
        "Type de graphique",
        [CHART_RADAR, CHART_SCATTER, CHART_TABLE],
        horizontal=True,
        key="chart_type",
        label_visibility="collapsed",
    )
    if chart_type == CHART_RADAR:
        radar.render(pop, players, pct_mode)
    elif chart_type == CHART_SCATTER:
        scatter.render(pop, players, pct_mode)
    else:
        table.render(pop, selected_names, pct_mode)


def _info_bar(pop: pd.DataFrame) -> None:
    combos = st.session_state.get("pos_sel_combos", set())
    pos_str = ""
    if combos:
        mode = st.session_state.get("pos_filter_mode", "OU")
        pos_str = f" · Poste ({mode}) : " + ", ".join(
            (p if s is None else f"{p}({s})") for p, s in sorted(combos)
        )
    st.markdown(
        f"<p style='color:#555; font-size:13px; margin-top:4px'>"
        f"{len(pop)} joueurs · Ajustements par club{pos_str}"
        f"</p>",
        unsafe_allow_html=True,
    )


def _collect_players(pop: pd.DataFrame, names: list[str]) -> list[dict]:
    """Moyenne des stats numériques de chaque joueur sélectionné."""
    num_cols = pop.select_dtypes(include="number").columns
    players = []
    for name in names:
        rows = pop[pop["Name"] == name]
        if rows.empty:
            st.warning(f"'{name}' introuvable dans la population filtrée.")
            continue
        players.append(
            {
                "name": name,
                "row": rows[num_cols].mean(),
                "score": float(rows[SCORE_COL].mean()),
            }
        )
    return players
