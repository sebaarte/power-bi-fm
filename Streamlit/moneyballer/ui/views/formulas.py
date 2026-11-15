"""Vue Formules : création et édition des scores personnalisés."""

import pandas as pd
import streamlit as st

from moneyballer.analysis import stat_columns
from moneyballer.storage import save_custom_cols
from moneyballer.ui.components import section_title


def render(pop: pd.DataFrame) -> None:
    section_title("Colonnes personnalisées")
    st.caption(
        "Choisissez plusieurs statistiques pour créer votre propre score. "
        "Le score final est la moyenne des percentiles de chaque statistique sélectionnée. "
        "Les colonnes créées sont disponibles dans le radar et le scatter."
    )
    if st.session_state.custom_cols:
        section_title("Formules existantes")
        num_cols = stat_columns(pop)
        for i, formula in enumerate(st.session_state.custom_cols):
            _render_existing(i, formula, num_cols)
    _render_new(pop)


def _render_existing(i: int, formula: dict, num_cols: list[str]) -> None:
    editing_key = f"editing_cc_{i}"
    is_editing = st.session_state.get(editing_key, False)
    with st.expander(f"**{formula['name']}**", expanded=is_editing):
        if is_editing:
            _render_edit_form(i, formula, num_cols, editing_key)
            return
        st.markdown("  \n".join(c["col"] for c in formula["components"]))
        c_edit, c_del = st.columns(2)
        with c_edit:
            if st.button("✏️ Modifier", key=f"edit_cc_{i}"):
                st.session_state[editing_key] = True
                st.rerun()
        with c_del:
            if st.button("🗑 Supprimer", key=f"del_cc_{i}"):
                st.session_state.custom_cols = [
                    c for j, c in enumerate(st.session_state.custom_cols) if j != i
                ]
                save_custom_cols(st.session_state.custom_cols)
                st.rerun()


def _close_editor(editing_key: str, *temp_keys: str) -> None:
    st.session_state[editing_key] = False
    for k in temp_keys:
        st.session_state.pop(k, None)
    st.rerun()


def _render_edit_form(
    i: int, formula: dict, num_cols: list[str], editing_key: str
) -> None:
    name_key, cols_key = f"edit_name_{i}", f"edit_cols_{i}"
    if name_key not in st.session_state:
        st.session_state[name_key] = formula["name"]
    if cols_key not in st.session_state:
        st.session_state[cols_key] = [
            c["col"] for c in formula["components"] if c["col"] in num_cols
        ]
    new_name = st.text_input("Nom de la colonne", key=name_key)
    other_names = {
        o["name"] for j, o in enumerate(st.session_state.custom_cols) if j != i
    }
    new_cols = st.multiselect(
        "Colonnes à combiner",
        options=[c for c in num_cols if c not in other_names],
        key=cols_key,
    )
    c_save, c_cancel = st.columns(2)
    with c_save:
        if st.button(
            "✅ Enregistrer",
            key=f"save_cc_{i}",
            disabled=not (new_name.strip() and new_cols),
        ):
            formulas = list(st.session_state.custom_cols)
            formulas[i] = {
                "name": new_name.strip(),
                "components": [{"col": c} for c in new_cols],
            }
            st.session_state.custom_cols = formulas
            save_custom_cols(formulas)
            _close_editor(editing_key, name_key, cols_key)
    with c_cancel:
        if st.button("✗ Annuler", key=f"cancel_cc_{i}"):
            _close_editor(editing_key, name_key, cols_key)


def _render_new(pop: pd.DataFrame) -> None:
    section_title("Nouvelle formule")
    existing = {cc["name"] for cc in st.session_state.custom_cols}
    name = st.text_input(
        "Nom de la colonne",
        key="formula_name",
        placeholder="ex: Mon Score Offensif",
    )
    cols = st.multiselect(
        "Colonnes à combiner",
        options=[c for c in stat_columns(pop) if c not in existing],
        key="formula_cols",
    )
    weights: dict = {}
    if cols:
        section_title("Poids")
        grid = st.columns(min(3, len(cols)))
        for k, col in enumerate(cols):
            with grid[k % len(grid)]:
                weights[col] = st.number_input(
                    col, value=1.0, step=0.1, format="%.3g", key=f"fw_{col}"
                )

    if st.button(
        "✅ Créer la formule",
        disabled=not (name.strip() and cols),
        key="btn_create_cc",
    ):
        new = {
            "name": name.strip(),
            "components": [{"col": c, "weight": float(weights[c])} for c in cols],
        }
        st.session_state.custom_cols = [
            c for c in st.session_state.custom_cols if c["name"] != new["name"]
        ] + [new]
        save_custom_cols(st.session_state.custom_cols)
        st.success(f"✓ '{new['name']}' créée")
        st.rerun()
