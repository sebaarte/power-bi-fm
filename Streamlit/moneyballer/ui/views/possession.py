"""Vue Possession : possession moyenne par club."""

import streamlit as st

from moneyballer.storage import save_adj_settings
from moneyballer.ui.components import section_title


def _save_and_rerun() -> None:
    save_adj_settings(st.session_state.adj_df, st.session_state.ligue_mod)
    st.rerun()


def render() -> None:
    section_title("Possession par club / ligue")
    st.caption(
        "Possession moyenne de l'équipe (0.50 = 50 %). "
        "Utilisée pour normaliser les stats défensives /90."
    )
    adj_df = st.session_state.adj_df
    edited = st.data_editor(
        adj_df[["Club", "Possession"]].copy(),
        key="poss_editor",
        column_config={
            "Club": st.column_config.TextColumn("Club", disabled=True),
            "Possession": st.column_config.NumberColumn(
                "Possession", min_value=0.01, max_value=1.0, step=0.01, format="%.2f"
            ),
        },
        hide_index=True,
        num_rows="fixed",
    )
    changed = (
        edited["Possession"].round(4).tolist() != adj_df["Possession"].round(4).tolist()
    )
    c_apply, c_reset = st.columns([3, 1])
    with c_apply:
        if st.button(
            "✅ Appliquer les possessions", key="btn_apply_poss", disabled=not changed
        ):
            adj_df["Possession"] = edited["Possession"].values
            _save_and_rerun()
    with c_reset:
        if st.button("🔄 Reset", key="btn_reset_poss"):
            adj_df["Possession"] = 0.5
            _save_and_rerun()
