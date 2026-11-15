"""Petits composants HTML / helpers de widgets réutilisés par les vues."""

from html import escape

import streamlit as st


def section_title(text: str, margin_top: int | None = None) -> None:
    style = f" style='margin-top:{margin_top}px'" if margin_top is not None else ""
    st.markdown(
        f"<div class='section-title'{style}>{escape(text)}</div>",
        unsafe_allow_html=True,
    )


def player_tag(label: str, color: str) -> str:
    return (
        f"<span class='player-tag' style='background:{color}22; color:{color};"
        f" border:1px solid {color}55'>{escape(label)}</span>"
    )


def metric_card(label: str, value, font_size: int | None = None) -> str:
    style = f" style='font-size:{font_size}px'" if font_size else ""
    return (
        f"<div class='metric-card'><div class='metric-label'>{escape(label)}</div>"
        f"<div class='metric-value'{style}>{escape(str(value))}</div></div>"
    )


def prune_selection(key: str, options: list) -> None:
    """Retire de l'état d'un multiselect les valeurs qui ne sont plus proposées."""
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in options]
