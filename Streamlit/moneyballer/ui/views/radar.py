"""Onglet Radar : dashboard multi-formules ou radar personnalisé."""

from html import escape

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from moneyballer.analysis import (
    build_radar_players,
    compute_refs,
    percentile_of,
    stat_columns,
)
from moneyballer.charts.radar import draw_radar, radar_labels
from moneyballer.config import (
    BEST_COLOR,
    MEAN_COLOR,
    P95_COLOR,
    PLAYER_COLORS,
    SCORE_COL,
)
from moneyballer.ui.components import (
    metric_card,
    player_tag,
    prune_selection,
    section_title,
)

MODE_DASHBOARD = "🧮 Dashboard formules"
MODE_CUSTOM = "🛠 Radar personnalisé"
NO_TEMPLATE = "— Aucun —"
GRID_SIZES = [1, 2, 3, 4]
# Streamlit purge l'état des widgets non affichés : copie hors widget pour garder la sélection
_SAVED_FORMULAS = "_radar_formulas_saved"

INFO_COLS = [
    "Name",
    "Club",
    "Division",
    "Position",
    "Age",
    "Nat",
    "Mins",
    "Apps",
    "Wage",
    "Transfer Value",
    "Preferred Foot",
    "Personality",
]


def render(pop: pd.DataFrame, players: list[dict], pct_mode: bool) -> None:
    mode = st.radio(
        "Mode radar",
        [MODE_DASHBOARD, MODE_CUSTOM],
        horizontal=True,
        key="radar_view_mode",
        label_visibility="collapsed",
    )
    if mode == MODE_DASHBOARD:
        _render_dashboard(pop, players, pct_mode)
    else:
        _render_custom(pop, players, pct_mode)


def _player_color(i: int) -> str:
    return PLAYER_COLORS[i % len(PLAYER_COLORS)]


# ══════════════════════════════════════════════════════════════════
# DASHBOARD MULTI-FORMULES
# ══════════════════════════════════════════════════════════════════
def _render_dashboard(pop: pd.DataFrame, players: list[dict], pct_mode: bool) -> None:
    formulas = {
        cc["name"]: cc
        for cc in st.session_state.get("custom_cols", [])
        if cc["name"] in pop.columns
    }
    if not formulas:
        st.info("Aucune formule disponible — crée-en dans la vue 🧮 Formules.")
        return

    names = list(formulas)
    saved = st.session_state.get(
        "radar_formulas", st.session_state.get(_SAVED_FORMULAS, [])
    )
    st.session_state["radar_formulas"] = [n for n in saved if n in names]

    c_sel, c_grid = st.columns([5, 1])
    with c_sel:
        chosen = st.multiselect(
            "📋 Formules à afficher",
            options=names,
            key="radar_formulas",
            placeholder="Choisir une ou plusieurs formules…",
        )
    with c_grid:
        n_cols = st.selectbox(
            "Colonnes", options=GRID_SIZES, index=1, key="radar_grid_cols"
        )
    st.session_state[_SAVED_FORMULAS] = chosen

    if not chosen:
        st.info("Sélectionne une ou plusieurs formules pour construire le dashboard.")
        return

    _dashboard_legend(players)
    for start in range(0, len(chosen), n_cols):
        for slot, name in zip(st.columns(n_cols), chosen[start : start + n_cols]):
            with slot:
                _formula_card(pop, formulas[name], players, pct_mode)

    _scores_summary(pop, chosen, players, pct_mode)


def _dashboard_legend(players: list[dict]) -> None:
    items = [
        ("Moyenne", MEAN_COLOR, "dashed"),
        ("P95", P95_COLOR, "dashed"),
        ("Meilleur de la formule", BEST_COLOR, "solid"),
    ] + [(p["name"], _player_color(i), "solid") for i, p in enumerate(players)]
    html = "".join(
        f"<span class='legend-item'><span class='legend-line' "
        f"style='border-top:3px {style} {color}'></span>{escape(label)}</span>"
        for label, color, style in items
    )
    st.markdown(f"<div class='radar-legend'>{html}</div>", unsafe_allow_html=True)


def _formula_card(
    pop: pd.DataFrame, formula: dict, players: list[dict], pct_mode: bool
) -> None:
    name = formula["name"]
    cols = [c["col"] for c in formula["components"] if c["col"] in pop.columns]
    with st.container(border=True):
        st.markdown(
            f"<div class='card-title'>{escape(name)}</div>", unsafe_allow_html=True
        )
        if len(cols) < 3:
            st.warning("Au moins 3 composantes sont nécessaires pour tracer le radar.")
            return

        refs, best_name = compute_refs(pop, cols, pct_mode, name)
        radar_players = build_radar_players(players, pop, refs, cols, pct_mode, name)
        fig = draw_radar(
            refs,
            best_name,
            radar_players,
            cols,
            radar_labels(cols),
            figsize=(6, 6),
            show_legend=False,
        )
        st.pyplot(fig)
        plt.close(fig)

        tags = [player_tag(f"⭐ {best_name} — {pop[name].max():.2f}", BEST_COLOR)]
        tags += [
            player_tag(f"{p['name']} — {p['score']:.2f}", _player_color(i))
            for i, p in enumerate(radar_players)
        ]
        st.markdown(" ".join(tags), unsafe_allow_html=True)


def _scores_summary(
    pop: pd.DataFrame, names: list[str], players: list[dict], pct_mode: bool
) -> None:
    """Tableau joueurs × formules (barres de progression)."""
    section_title("Synthèse des scores", margin_top=30)
    if pct_mode:
        rows = {
            "— Moyenne": {n: 50.0 for n in names},
            "— P95": {n: 95.0 for n in names},
        }
        rows |= {
            p["name"]: {n: percentile_of(pop, n, p["row"][n]) for n in names}
            for p in players
        }
        max_value, fmt = 100, "%.1f %%"
    else:
        rows = {
            "— Moyenne": pop[names].mean().to_dict(),
            "— P95": pop[names].quantile(0.95).to_dict(),
        }
        rows |= {p["name"]: {n: float(p["row"][n]) for n in names} for p in players}
        max_value, fmt = 1, "%.2f"

    st.dataframe(
        pd.DataFrame.from_dict(rows, orient="index")[names].rename_axis("Joueur"),
        column_config={
            n: st.column_config.ProgressColumn(
                n, min_value=0, max_value=max_value, format=fmt
            )
            for n in names
        },
    )


# ══════════════════════════════════════════════════════════════════
# RADAR PERSONNALISÉ
# ══════════════════════════════════════════════════════════════════
def _render_custom(pop: pd.DataFrame, players: list[dict], pct_mode: bool) -> None:
    num_cols = stat_columns(pop)
    _template_picker(pop, num_cols)

    prune_selection("custom_radar_cols", num_cols)
    radar_cols = st.multiselect(
        "Statistiques du radar (3 à 12)",
        options=num_cols,
        key="custom_radar_cols",
    )
    if st.session_state.get("radar_score_col") not in num_cols:
        st.session_state["radar_score_col"] = (
            SCORE_COL if SCORE_COL in num_cols else num_cols[0]
        )
    score_col = st.selectbox(
        "🏆 Métrique meilleur joueur", options=num_cols, key="radar_score_col"
    )

    if len(radar_cols) < 3:
        st.warning("Sélectionne au moins 3 dimensions pour afficher le radar.")
        return

    refs, best_name = compute_refs(pop, radar_cols, pct_mode, score_col)
    radar_players = build_radar_players(
        players, pop, refs, radar_cols, pct_mode, score_col
    )
    best_row = pop.loc[pop[score_col].idxmax()]

    col_radar, col_stats = st.columns([2, 1])
    with col_radar:
        fig = draw_radar(
            refs, best_name, radar_players, radar_cols, radar_labels(radar_cols)
        )
        st.pyplot(fig)
        plt.close(fig)
    with col_stats:
        _best_player_panel(best_row, score_col)
        _player_stats(pop, radar_players, radar_cols, pct_mode)

    if radar_players:
        _comparison_table(
            pop, radar_cols, score_col, best_name, best_row, radar_players, pct_mode
        )
        _general_info(pop, best_row, radar_players)


def _template_picker(pop: pd.DataFrame, num_cols: list[str]) -> None:
    """Charge les composantes d'une formule comme axes du radar."""
    templates = [
        cc for cc in st.session_state.get("custom_cols", []) if cc["name"] in num_cols
    ]
    if not templates:
        return
    c_sel, c_btn = st.columns([4, 1], vertical_alignment="bottom")
    with c_sel:
        chosen = st.selectbox(
            "📋 Template formule",
            options=[NO_TEMPLATE] + [cc["name"] for cc in templates],
            key="radar_template",
            help=(
                "Applique une formule personnalisée : axes du radar = "
                "composantes de la formule, métrique meilleur joueur = formule."
            ),
        )
    with c_btn:
        if st.button(
            "Appliquer", key="btn_apply_radar_tpl", disabled=chosen == NO_TEMPLATE
        ):
            tpl = next(cc for cc in templates if cc["name"] == chosen)
            st.session_state.custom_radar_cols = [
                c["col"] for c in tpl["components"] if c["col"] in pop.columns
            ]
            st.session_state.radar_score_col = tpl["name"]
            st.rerun()


def _best_player_panel(best_row: pd.Series, score_col: str) -> None:
    section_title("Meilleur joueur")
    html = metric_card("Nom", best_row["Name"], font_size=20) + metric_card(
        score_col, f"{best_row.get(score_col, 0.0):.2f}"
    )
    if "Club" in best_row.index:
        html += metric_card("Club", best_row.get("Club", "—"), font_size=18)
    st.markdown(html, unsafe_allow_html=True)


def _player_stats(
    pop: pd.DataFrame, radar_players: list[dict], cols: list[str], pct_mode: bool
) -> None:
    if not radar_players:
        return
    section_title("Stats percentiles" if pct_mode else "Stats brutes (ajustées)")
    for i, p in enumerate(radar_players):
        st.markdown(
            player_tag(f"{p['name']} — {p['score']:.2f}", _player_color(i)),
            unsafe_allow_html=True,
        )
        if pct_mode:
            display = {
                c: f"{percentile_of(pop, c, p['raw'].get(c, 0)):.1f} %"
                for c in cols
                if c in pop.columns
            }
        else:
            display = {c: f"{p['raw'].get(c, 0):.2f}" for c in cols}
        st.dataframe(
            pd.DataFrame({"Valeur": display}),
            height=min(280, 38 * len(cols) + 38),
        )


def _comparison_table(
    pop: pd.DataFrame,
    cols: list[str],
    score_col: str,
    best_name: str,
    best_row: pd.Series,
    radar_players: list[dict],
    pct_mode: bool,
) -> None:
    section_title("Tableau comparatif", margin_top=30)
    table_cols = cols + ([score_col] if score_col not in cols else [])

    def fmt(col: str, value: float) -> str:
        if pct_mode:
            return f"{percentile_of(pop, col, value):.1f} %"
        return f"{value:.2f}"

    rows = {
        "— Moyenne": {
            c: "50.0 %" if pct_mode else f"{pop[c].mean():.2f}" for c in table_cols
        },
        "— P95": {
            c: "95.0 %" if pct_mode else f"{pop[c].quantile(0.95):.2f}"
            for c in table_cols
        },
        f"⭐ {best_name}": {c: fmt(c, best_row[c]) for c in table_cols},
    }
    for p in radar_players:
        values = {c: p["raw"].get(c, 0) for c in cols}
        if score_col not in cols:
            values[score_col] = p["score"]
        rows[p["name"]] = {c: fmt(c, v) for c, v in values.items()}

    st.dataframe(pd.DataFrame.from_dict(rows, orient="index").rename_axis("Joueur"))


def _general_info(
    pop: pd.DataFrame, best_row: pd.Series, radar_players: list[dict]
) -> None:
    cols = [c for c in INFO_COLS if c in pop.columns]
    if not cols:
        return
    section_title("Infos générales", margin_top=30)
    best = {c: best_row[c] for c in cols}
    best["Name"] = f"⭐ {best_row['Name']}"
    rows = [best]
    for p in radar_players:
        matches = pop[pop["Name"] == p["name"]]
        if not matches.empty:
            rows.append(matches.iloc[0][cols].to_dict())
    st.dataframe(pd.DataFrame(rows), hide_index=True)
