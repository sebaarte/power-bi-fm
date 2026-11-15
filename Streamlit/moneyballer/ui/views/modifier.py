"""Vue Modificateur : facteur de difficulté par ligue."""

import pandas as pd
import streamlit as st

from moneyballer.storage import save_adj_settings
from moneyballer.ui.components import section_title


def render() -> None:
    section_title("Modificateur par ligue")
    st.caption(
        "Facteur de difficulté par ligue (1.0 = neutre). "
        "Appliqué à tous les clubs de la ligue."
    )
    ligues = sorted(st.session_state.adj_df["Ligue"].dropna().unique().tolist())
    current = pd.DataFrame(
        {
            "Ligue": ligues,
            "Modificateur": [st.session_state.ligue_mod.get(lg, 1.0) for lg in ligues],
        }
    )
    edited = st.data_editor(
        current.copy(),
        key="mod_editor",
        column_config={
            "Ligue": st.column_config.TextColumn("Ligue", disabled=True),
            "Modificateur": st.column_config.NumberColumn(
                "Modificateur", min_value=0.1, max_value=10.0, step=0.05, format="%.2f"
            ),
        },
        hide_index=True,
        num_rows="fixed",
    )
    new_map = dict(zip(edited["Ligue"], edited["Modificateur"].round(4)))
    old_map = dict(zip(current["Ligue"], current["Modificateur"].round(4)))
    if st.button(
        "✅ Appliquer les modificateurs",
        key="btn_apply_mod",
        disabled=new_map == old_map,
    ):
        st.session_state.ligue_mod = {lg: float(v) for lg, v in new_map.items()}
        save_adj_settings(st.session_state.adj_df, st.session_state.ligue_mod)
        st.rerun()
