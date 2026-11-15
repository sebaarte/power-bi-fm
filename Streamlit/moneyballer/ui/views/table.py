"""Onglet Tableau : liste filtrable, synchronisée avec la sélection de joueurs."""

import pandas as pd
import streamlit as st

from moneyballer.analysis import stat_columns
from moneyballer.config import MAX_PLAYERS
from moneyballer.ui.components import prune_selection

FIXED_COLS = ["Name", "Club", "Position", "Age", "Mins", "Apps", "Transfer Value"]
NO_TEMPLATE = "— Aucun —"
HIGHLIGHT_STYLE = "background-color: #fffde7; color: #1a1a1a"


def render(pop: pd.DataFrame, selected_names: list[str], pct_mode: bool) -> None:
    num_cols = stat_columns(pop)
    active_formula = _formula_picker(pop, num_cols)

    if "tbl_extra_cols" not in st.session_state:
        st.session_state.tbl_extra_cols = []
    prune_selection("tbl_extra_cols", num_cols)
    extra_cols = st.multiselect(
        "Colonnes supplémentaires", options=num_cols, key="tbl_extra_cols"
    )

    fixed = [c for c in FIXED_COLS if c in pop.columns]
    stat_cols = [c for c in extra_cols if c not in fixed]
    if active_formula and active_formula not in stat_cols:
        stat_cols = [active_formula] + stat_cols
    all_cols = fixed + stat_cols

    df = pop[[c for c in all_cols if c in pop.columns]].copy()
    pct_cols = [
        c
        for c in stat_cols
        if c in pop.columns and pd.api.types.is_numeric_dtype(pop[c])
    ]
    if pct_mode:
        for c in pct_cols:
            df[c] = pop[c].rank(pct=True).mul(100).round(1)

    view = _apply_table_filters(df, all_cols)

    # Réinitialiser la sélection de lignes si le filtre change
    view_hash = hash(tuple(view.index.tolist()))
    if st.session_state.get("_tbl_view_hash") != view_hash:
        st.session_state["_tbl_row_sel"] = []
        st.session_state["_tbl_view_hash"] = view_hash

    styled = (
        view.style.apply(
            lambda row: (
                [HIGHLIGHT_STYLE if row.get("Name", "") in selected_names else ""]
                * len(row)
            ),
            axis=1,
        )
        if "Name" in view.columns
        else view
    )
    event = st.dataframe(
        styled,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            c: st.column_config.NumberColumn(c, format="%.1f %%")
            for c in pct_cols
            if pct_mode
        },
    )
    st.caption(
        "Cliquez sur une ligne pour ajouter / retirer le joueur de la sélection."
    )
    _sync_selection(view, event.selection.rows, selected_names)


def _formula_picker(pop: pd.DataFrame, num_cols: list[str]) -> str | None:
    """Retourne la formule active ; « Appliquer » charge ses composantes en colonnes."""
    templates = [
        cc for cc in st.session_state.get("custom_cols", []) if cc["name"] in num_cols
    ]
    if not templates:
        return None
    c_sel, c_btn = st.columns([4, 1], vertical_alignment="bottom")
    with c_sel:
        chosen = st.selectbox(
            "📋 Charger une formule",
            options=[NO_TEMPLATE] + [cc["name"] for cc in templates],
            key="tbl_template",
        )
    with c_btn:
        if st.button(
            "Appliquer", key="btn_apply_tbl_tpl", disabled=chosen == NO_TEMPLATE
        ):
            tpl = next(cc for cc in templates if cc["name"] == chosen)
            st.session_state.tbl_extra_cols = [
                c["col"] for c in tpl["components"] if c["col"] in pop.columns
            ]
            st.rerun()
    return None if chosen == NO_TEMPLATE else chosen


def _column_filter(df: pd.DataFrame, col: str) -> tuple:
    if pd.api.types.is_numeric_dtype(df[col]):
        c_lo, c_hi = st.columns(2)
        with c_lo:
            lo = st.number_input(
                f"{col} ≥", value=float(df[col].min()), key=f"tbl_flo_{col}"
            )
        with c_hi:
            hi = st.number_input(
                f"{col} ≤", value=float(df[col].max()), key=f"tbl_fhi_{col}"
            )
        return ("num", lo, hi)
    text = st.text_input(f"{col} contient", key=f"tbl_ftxt_{col}", placeholder="…")
    return ("txt", text)


def _apply_table_filters(df: pd.DataFrame, all_cols: list[str]) -> pd.DataFrame:
    """Filtres d'affichage uniquement (ne modifient pas la population)."""
    present = [c for c in all_cols if c in df.columns]
    txt_cols = [c for c in present if not pd.api.types.is_numeric_dtype(df[c])]
    num_cols = [c for c in present if pd.api.types.is_numeric_dtype(df[c])]

    with st.expander("🔍 Filtres du tableau", expanded=False):
        name_q = st.text_input(
            "Recherche nom", key="tbl_name_search", placeholder="Contient…"
        )
        filter_cols = st.multiselect(
            "Autres colonnes à filtrer",
            options=txt_cols + num_cols,
            key="tbl_filter_cols_sel",
        )
        filters = {c: _column_filter(df, c) for c in filter_cols}

    view = df
    if name_q and "Name" in view.columns:
        view = view[view["Name"].astype(str).str.contains(name_q, case=False, na=False)]
    for col, f in filters.items():
        if f[0] == "num":
            view = view[(view[col] >= f[1]) & (view[col] <= f[2])]
        elif f[1]:
            view = view[view[col].astype(str).str.contains(f[1], case=False, na=False)]
    return view


def _sync_selection(
    view: pd.DataFrame, curr_rows: list[int], selected_names: list[str]
) -> None:
    """Répercute les clics du tableau sur la sélection de joueurs de la sidebar."""
    if "Name" not in view.columns:
        return
    prev_rows = st.session_state.get("_tbl_row_sel", [])
    st.session_state["_tbl_row_sel"] = curr_rows
    if sorted(curr_rows) == sorted(prev_rows):
        return

    prev_names = {view.iloc[i]["Name"] for i in prev_rows if i < len(view)}
    curr_names = {view.iloc[i]["Name"] for i in curr_rows if i < len(view)}
    new_sel = [n for n in selected_names if n not in prev_names - curr_names]
    for n in curr_names - prev_names:
        if n not in new_sel and len(new_sel) < MAX_PLAYERS:
            new_sel.append(n)
    if set(new_sel) != set(selected_names):
        st.session_state["_pending_selected_names"] = new_sel
        st.rerun()
