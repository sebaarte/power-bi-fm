"""Barre latérale : source de données, filtres de population et sélection des joueurs."""

import os
from html import escape

import pandas as pd
import streamlit as st

from moneyballer.analysis import stat_columns
from moneyballer.config import MAX_PLAYERS
from moneyballer.data.adjustments import apply_adjustments
from moneyballer.data.loader import (
    build_dataset,
    latest_export,
    load_from_path,
    load_from_upload,
)
from moneyballer.data.metrics import apply_formulas
from moneyballer.storage import load_adj_settings, load_custom_cols
from moneyballer.ui.components import section_title

# None = case vide non cliquable
POS_GRID = [
    [None, ("ST", "C"), None],
    [("AM", "L"), ("AM", "C"), ("AM", "R")],
    [("M", "L"), ("M", "C"), ("M", "R")],
    [("WB", "L"), ("DM", None), ("WB", "R")],
    [("D", "L"), ("D", "C"), ("D", "R")],
    [None, ("GK", None), None],
]
POS_ROW_LABELS = ["ST", "AM", "M", "WB/DM", "D", "GK"]


def render() -> tuple[pd.DataFrame, list[str]]:
    """Affiche la barre latérale et retourne (population filtrée, joueurs sélectionnés)."""
    st.markdown(
        "<h2 style='font-size:1.3rem'>⚙️ Configuration</h2>", unsafe_allow_html=True
    )
    df_raw, source_key = _load_source()
    _sync_adjustments(df_raw)
    df_adj = _adjusted_df(df_raw, source_key)

    section_title("Filtres population")
    _position_selector()
    min_mins = st.slider(
        "Minutes minimum",
        0,
        int(df_raw["Mins"].max()) if "Mins" in df_raw.columns else 90,
        90,
        step=90,
    )
    adv_filters = _advanced_filters(df_adj)

    section_title("Joueurs à comparer")
    pop = _filter_population(df_adj, min_mins, adv_filters)
    if pop.empty:
        st.warning("Aucun joueur ne correspond aux filtres.")
        st.stop()

    if "custom_cols" not in st.session_state:
        st.session_state.custom_cols = load_custom_cols()
    pop = apply_formulas(pop, st.session_state.custom_cols)

    st.caption(f"{len(pop)} joueurs dans la population de référence")
    return pop, _player_selector(pop)


# ── Source & ajustements ─────────────────────────────────────────
CONCAT_HELP = (
    "Les joueurs présents dans les deux fichiers (même UID) sont fusionnés : "
    "totaux additionnés, stats /90 et % recalculées sur les minutes cumulées, "
    "attributs (club, âge, valeur…) repris du second fichier."
)


def _pick_source(
    path_label: str, upload_label: str, default_path: str, hint: str
) -> tuple[str, object] | None:
    """(clé, source) d'un CSV ; un fichier importé prime sur le chemin."""
    csv_path = st.text_input(path_label, value=default_path)
    uploaded = st.file_uploader(upload_label, type=["csv"])
    if uploaded is not None:
        return f"{uploaded.name}{uploaded.size}", uploaded
    if os.path.isfile(csv_path):
        return csv_path, csv_path
    st.info(hint)
    return None


def _load_source() -> tuple[pd.DataFrame, str]:
    section_title("Source de données")
    first = _pick_source(
        "Chemin du fichier CSV",
        "… ou importer un fichier",
        latest_export(),
        "Indique le chemin du CSV ou importe un fichier.",
    )
    if first is None:
        st.stop()
    sources = [first]
    if st.checkbox("➕ Concaténer un second CSV", key="concat_csv", help=CONCAT_HELP):
        second = _pick_source(
            "Chemin du second CSV",
            "… ou importer le second fichier",
            "",
            "Indique le chemin du second CSV ou importe un fichier.",
        )
        if second is not None:
            sources.append(second)

    # Reconstruit seulement si les sources changent
    source_key = "|".join(key for key, _ in sources)
    if st.session_state.get("_src_key") != source_key:
        try:
            frames = [
                load_from_path(src) if isinstance(src, str) else load_from_upload(src)
                for _, src in sources
            ]
            st.session_state._df_raw = build_dataset(frames)
        except Exception as e:
            st.error(f"Erreur chargement : {e}")
            st.stop()
        st.session_state._src_rows = sum(len(f) for f in frames)
        st.session_state._src_key = source_key

    df_raw = st.session_state._df_raw
    n_merged = st.session_state._src_rows - len(df_raw)
    st.success(
        f"{len(df_raw)} joueurs chargés"
        + (f" ({n_merged} fusionnés)" if len(sources) > 1 else "")
    )
    return df_raw, source_key


def _default_adj_df(df_raw: pd.DataFrame, clubs: list) -> pd.DataFrame:
    div_map = (
        df_raw.groupby("Club")["Division"].first().to_dict()
        if "Division" in df_raw.columns
        else {}
    )
    return pd.DataFrame(
        {
            "Club": clubs,
            "Ligue": [div_map.get(c, "") for c in clubs],
            "Possession": [0.5] * len(clubs),
        }
    )


def _sync_adjustments(df_raw: pd.DataFrame) -> None:
    """Initialise / complète st.session_state.adj_df et ligue_mod."""
    clubs = (
        sorted(df_raw["Club"].dropna().unique().tolist())
        if "Club" in df_raw.columns
        else []
    )
    if "adj_df" not in st.session_state:
        adj_df = _default_adj_df(df_raw, clubs)
        club_settings, ligue_mod = load_adj_settings()
        for club, rec in club_settings.items():
            m = adj_df["Club"] == club
            if m.any():
                adj_df.loc[m, "Possession"] = float(rec.get("Possession", 0.5))
        st.session_state.adj_df = adj_df
        st.session_state.ligue_mod = ligue_mod
        return

    existing = set(st.session_state.adj_df["Club"].tolist())
    new_clubs = [c for c in clubs if c not in existing]
    if new_clubs:
        st.session_state.adj_df = pd.concat(
            [st.session_state.adj_df, _default_adj_df(df_raw, new_clubs)],
            ignore_index=True,
        )
    if "ligue_mod" not in st.session_state:
        _, st.session_state.ligue_mod = load_adj_settings()


def _adjusted_df(df_raw: pd.DataFrame, source_key: str) -> pd.DataFrame:
    """df_raw ajusté, recalculé seulement si la source ou les réglages changent."""
    sig = (
        source_key,
        int(pd.util.hash_pandas_object(st.session_state.adj_df).sum()),
        hash(frozenset(st.session_state.ligue_mod.items())),
    )
    if "df_adj" not in st.session_state or st.session_state.get("_adj_sig") != sig:
        st.session_state.df_adj = apply_adjustments(
            df_raw, st.session_state.adj_df, st.session_state.ligue_mod
        )
        st.session_state._adj_sig = sig
    return st.session_state.df_adj


# ── Filtres ──────────────────────────────────────────────────────
def _pos_label(pos: str, side: str | None) -> str:
    return pos if side is None else f"{pos}({side})"


def _position_selector() -> None:
    section_title("Poste")
    if "pos_filter_mode" not in st.session_state:
        st.session_state["pos_filter_mode"] = "OU"
    if "pos_sel_combos" not in st.session_state:
        st.session_state["pos_sel_combos"] = set()

    mode = st.session_state["pos_filter_mode"]
    c_or, c_and, c_reset = st.columns(3)
    for col, label, key in ((c_or, "OU", "btn_pos_or"), (c_and, "ET", "btn_pos_and")):
        with col:
            if st.button(
                label,
                key=key,
                type="primary" if mode == label else "secondary",
                width="stretch",
            ):
                st.session_state["pos_filter_mode"] = label
                st.rerun()
    with c_reset:
        if st.button("✕ Reset", key="btn_pos_reset", width="stretch"):
            st.session_state["pos_sel_combos"] = set()
            st.rerun()

    selected = st.session_state["pos_sel_combos"]
    for row_label, row in zip(POS_ROW_LABELS, POS_GRID):
        cells = st.columns([0.7, 1, 1, 1])
        cells[0].markdown(
            f"<div style='font-size:10px;color:#666;text-align:right;"
            f"margin-top:6px;padding-right:4px'>{row_label}</div>",
            unsafe_allow_html=True,
        )
        for cell_col, cell in zip(cells[1:], row):
            with cell_col:
                if cell is None:
                    st.markdown(" ")
                    continue
                is_sel = cell in selected
                if st.button(
                    _pos_label(*cell),
                    key=f"posbtn_{cell[0]}_{cell[1]}",
                    type="primary" if is_sel else "secondary",
                    width="stretch",
                ):
                    if is_sel:
                        selected.discard(cell)
                    else:
                        selected.add(cell)
                    st.rerun()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_bound(text, fallback: float, s_min: float, s_max: float) -> float:
    try:
        return _clamp(float(text), s_min, s_max)
    except (ValueError, TypeError):
        return fallback


def _on_bound_text(s_key, lo_key, hi_key, s_min, s_max) -> None:
    """Synchronise le slider après saisie d'une borne."""
    cur_lo, cur_hi = st.session_state[s_key]
    lo = _parse_bound(st.session_state[lo_key], cur_lo, s_min, s_max)
    hi = _parse_bound(st.session_state[hi_key], cur_hi, s_min, s_max)
    st.session_state[s_key] = (min(lo, hi), max(lo, hi))


def _on_slider(s_key, lo_key, hi_key) -> None:
    lo, hi = st.session_state[s_key]
    st.session_state[lo_key] = f"{lo:.6g}"
    st.session_state[hi_key] = f"{hi:.6g}"


def _range_filter(df: pd.DataFrame, col: str, pct_mode: bool) -> dict:
    """Slider + champs min/max synchronisés pour une colonne."""
    use_pct = pct_mode and col.lower() != "age"
    if use_pct:
        s_min, s_max, step = 0.0, 100.0, 1.0
    else:
        vals = df[col].dropna()
        s_min, s_max = float(vals.min()), float(vals.max())
        step = max((s_max - s_min) / 200, 0.01)

    s_key, lo_key, hi_key = f"adv_{col}", f"adv_lo_{col}", f"adv_hi_{col}"
    lo, hi = st.session_state.get(s_key, (s_min, s_max))
    st.session_state[s_key] = (_clamp(lo, s_min, s_max), _clamp(hi, s_min, s_max))
    cur_lo, cur_hi = st.session_state[s_key]
    if lo_key not in st.session_state:
        st.session_state[lo_key] = f"{cur_lo:.6g}"
    if hi_key not in st.session_state:
        st.session_state[hi_key] = f"{cur_hi:.6g}"

    st.markdown(
        f"<span style='font-size:12px;color:#aaa;letter-spacing:.08em'>"
        f"{escape(col)}</span>",
        unsafe_allow_html=True,
    )
    text_args = (s_key, lo_key, hi_key, s_min, s_max)
    c_lo, c_slider, c_hi = st.columns([1, 4, 1])
    with c_lo:
        st.text_input(
            "Min",
            key=lo_key,
            on_change=_on_bound_text,
            args=text_args,
            label_visibility="collapsed",
        )
    with c_slider:
        lo, hi = st.slider(
            col,
            s_min,
            s_max,
            key=s_key,
            step=float(f"{step:.3g}"),
            on_change=_on_slider,
            args=(s_key, lo_key, hi_key),
            label_visibility="collapsed",
        )
    with c_hi:
        st.text_input(
            "Max",
            key=hi_key,
            on_change=_on_bound_text,
            args=text_args,
            label_visibility="collapsed",
        )
    return {"lo": lo, "hi": hi, "pct": use_pct}


def _advanced_filters(df_adj: pd.DataFrame) -> dict:
    pct_mode = st.session_state.get("pct_mode", False)
    with st.expander("🔍 Filtres avancés", expanded=False):
        cols = st.multiselect(
            "Colonnes à filtrer",
            options=stat_columns(df_adj),
            default=[],
            key="adv_filter_cols",
        )
        return {col: _range_filter(df_adj, col, pct_mode) for col in cols}


def _filter_population(
    df_adj: pd.DataFrame, min_mins: int, adv_filters: dict
) -> pd.DataFrame:
    pop = df_adj.copy()
    combos = st.session_state.get("pos_sel_combos", set())
    if combos and "_pos_combos" in pop.columns:
        if st.session_state.get("pos_filter_mode", "OU") == "ET":
            pop = pop[pop["_pos_combos"].apply(lambda s: combos.issubset(s))]
        else:
            pop = pop[pop["_pos_combos"].apply(lambda s: bool(s & combos))]
    if "Mins" in pop.columns:
        pop = pop[pop["Mins"] >= min_mins]

    for col, f in adv_filters.items():
        if col not in pop.columns:
            continue
        if f["pct"]:
            pct = pop[col].rank(pct=True) * 100
            pop = pop[(pct >= f["lo"]) & (pct <= f["hi"])]
        else:
            pop = pop[(pop[col] >= f["lo"]) & (pop[col] <= f["hi"])]
    return pop


# ── Joueurs ──────────────────────────────────────────────────────
def _player_selector(pop: pd.DataFrame) -> list[str]:
    # Sélection en attente (depuis le tableau), à appliquer avant d'instancier le widget
    if "_pending_selected_names" in st.session_state:
        st.session_state["selected_names"] = st.session_state.pop(
            "_pending_selected_names"
        )
    return st.multiselect(
        f"Sélectionner jusqu'à {MAX_PLAYERS} joueurs",
        options=sorted(pop["Name"].dropna().unique().tolist()),
        max_selections=MAX_PLAYERS,
        key="selected_names",
    )
