"""Moneyballer — point d'entrée Streamlit.

Lancement : streamlit run app.py
"""

import streamlit as st

from moneyballer.ui import sidebar
from moneyballer.ui.style import inject_global_css
from moneyballer.ui.views import data, formulas, modifier, possession

VIEW_DATA = "📊 Data"
VIEW_POSSESSION = "⚽ Possession"
VIEW_MODIFIER = "🔧 Modificateur"
VIEW_FORMULAS = "🧮 Formules"


def main() -> None:
    st.set_page_config(
        page_title="Moneyballer",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()

    with st.sidebar:
        pop, selected_names = sidebar.render()

    st.markdown(
        "<h1 style='font-size:2.2rem; margin-bottom:0'>⚽ Defensive Radar</h1>",
        unsafe_allow_html=True,
    )
    view = st.selectbox(
        "Vue",
        options=[VIEW_DATA, VIEW_POSSESSION, VIEW_MODIFIER, VIEW_FORMULAS],
        key="view_sel",
        label_visibility="collapsed",
    )
    if view == VIEW_POSSESSION:
        possession.render()
    elif view == VIEW_MODIFIER:
        modifier.render()
    elif view == VIEW_FORMULAS:
        formulas.render(pop)
    else:
        data.render(pop, selected_names)


if __name__ == "__main__":
    main()
