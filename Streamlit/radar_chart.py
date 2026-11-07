import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import os
import json

# ── Persistence du fichier adj_settings ──────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADJ_SETTINGS_FILE = os.path.join(_SCRIPT_DIR, "adj_settings.json")


def _load_adj_settings() -> tuple:
    """Retourne (club_settings, ligue_mod).
    club_settings : {club: {Ligue, Possession}}
    ligue_mod     : {ligue: modificateur}
    """
    if os.path.exists(ADJ_SETTINGS_FILE):
        try:
            with open(ADJ_SETTINGS_FILE, "r", encoding="utf-8") as _f:
                data = json.load(_f)
            # Compatibilité ancien format (liste plate Club/Possession/Modificateur)
            if isinstance(data, list):
                return {r["Club"]: r for r in data if "Club" in r}, {}
            club_settings = {
                r["Club"]: r for r in data.get("possessions", []) if "Club" in r
            }
            ligue_mod = {
                r["Ligue"]: float(r["Modificateur"])
                for r in data.get("modificateurs", [])
                if "Ligue" in r
            }
            return club_settings, ligue_mod
        except Exception:
            pass
    return {}, {}


def _save_adj_settings(adj_df: pd.DataFrame, ligue_mod: dict) -> None:
    """Sauvegarde Possession par club + Modificateur par ligue."""
    try:
        possessions = adj_df[["Club", "Ligue", "Possession"]].to_dict(orient="records")
        modificateurs = [
            {"Ligue": lg, "Modificateur": mod} for lg, mod in ligue_mod.items()
        ]
        with open(ADJ_SETTINGS_FILE, "w", encoding="utf-8") as _f:
            json.dump(
                {"possessions": possessions, "modificateurs": modificateurs},
                _f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass


CUSTOM_COLS_FILE = os.path.join(_SCRIPT_DIR, "custom_cols.json")


def _load_custom_cols() -> list:
    """Retourne la liste des colonnes personnalisées depuis le fichier JSON."""
    if os.path.exists(CUSTOM_COLS_FILE):
        try:
            with open(CUSTOM_COLS_FILE, "r", encoding="utf-8") as _f:
                return json.load(_f)
        except Exception:
            pass
    return []


def _save_custom_cols(cols: list) -> None:
    """Sauvegarde la liste des colonnes personnalisées dans le fichier JSON."""
    try:
        with open(CUSTOM_COLS_FILE, "w", encoding="utf-8") as _f:
            json.dump(cols, _f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Moneyballer",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;600;700&family=Barlow:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Barlow', sans-serif; background-color: #0f0f13; color: #e0e0e0; }
    .stApp { background-color: #0f0f13; }
    h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif; letter-spacing: 0.05em; text-transform: uppercase; }
    section[data-testid="stSidebar"] { background-color: #16161e; border-right: 1px solid #2a2a3a; }
    .metric-card { background: linear-gradient(135deg, #1a1a28 0%, #16161e 100%); border: 1px solid #2a2a3a; border-radius: 8px; padding: 16px; margin-bottom: 8px; }
    .metric-label { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: #888; margin-bottom: 4px; }
    .metric-value { font-family: 'Barlow Condensed', sans-serif; font-size: 24px; font-weight: 700; color: #ffffff; }
    .player-tag { display: inline-block; padding: 4px 10px; border-radius: 3px; font-family: 'Barlow Condensed', sans-serif; font-size: 13px; font-weight: 600; letter-spacing: 0.05em; margin: 2px; }
    .section-title { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; color: #555; border-bottom: 1px solid #2a2a3a; padding-bottom: 6px; margin-bottom: 12px; margin-top: 20px; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Constantes ───────────────────────────────────────────────────
STATS_COLS = [
    "Clr/90",
    "Int/90",
    "Shts Blckd/90",
    "Pres C/90",
    "Tck/90",
    "K Tck/90",
    "Hdrs W/90",
]
STATS_LABELS = [
    "Clr/90",
    "Int/90",
    "Shts\nBlckd/90",
    "Pres C/90",
    "Tck/90",
    "K Tck/90",
    "Hdrs W/90",
]
SCORE_COL = "Defensive Actions/90"
PLAYER_COLORS = ["#ff4d4d", "#a259ff", "#00e676", "#ff9800", "#00e5ff"]

# ── Colonnes d'ajustement par catégorie ──────────────────────────
# Offensives : × Modifier × (0.5 / Possession)
OFF_COLS: frozenset = frozenset(
    {
        # CSV
        "Gls/90",
        "xG/90",
        "xG-OP",
        "NP-xG/90",
        "xA/90",
        "xA",
        "Shot/90",
        "ShT/90",
        "Shots Outside Box/90",
        "Shts Blckd/90",
        "K Ps/90",
        "OP-KP/90",
        "OP-Crs C/90",
        "OP-Crs A/90",
        "Cr C/90",
        "Crs A/90",
        "Drb/90",
        "Asts/90",
        "Ch C/90",
        "Ps C/90",
        "Ps A/90",
        "Pr passes/90",
        "Poss Lost/90",
        "Off",
        "Gl Mst",
        "CCC",
        "Gls",
        "xG",
        "NP-xG",
        "Ast",
        "Shots",
        "ShT",
        "Shts Blckd",
        "Pr Passes",
        "K Pas",
        "OP-KP",
        "OP-Crs C",
        "OP-Crs A",
        "Cr C",
        "Cr A",
        "Drb",
        "Pas A",
        "Ps C",
        # Calculées
        "xg Overperformance",
        "xg Overperformance/90",
        "Non pen goals",
        "Non pen goals/90",
        "Non pen xG Overperformance",
        "Non pen xG Overperformance/90",
        "Non-pen Goals - Non-pen xG/90",
        "xA Overperformance",
        "xA Overperformance/90",
        "Goal Contributions",
        "Goal Contributions/90",
        "xGC",
        "xGC/90",
        "xGC Overperformance",
        "xGC Overperformance/90",
        "Non-pen GC",
        "Non-pen GC/90",
        "Non-pen xGC",
        "Non-pen xGC Overperformance",
        "Non-pen xGC Overperformance/90",
        "Open Play Crosses Completed/90",
        "Open Play Crosses Attempted/90",
        "Clear Cut Chances/90",
        "Attacking Actions/90",
        "Creative Actions/90",
    }
)

# Défensives : × Modifier × (Possession / 0.5)
DEF_COLS: frozenset = frozenset(
    {
        # CSV
        "Tck/90",
        "K Tck/90",
        "Int/90",
        "Hdrs W/90",
        "Hdrs L/90",
        "Pres A/90",
        "Pres C/90",
        "Clr/90",
        "Blk/90",
        "Sprints/90",
        "Aer A/90",
        "Poss Won/90",
        "Con/90",
        "Conc",
        "Tck W",
        "Tck A",
        "K Tck",
        "Itc",
        "Hdrs",
        "Hdrs A",
        "Pres A",
        "Pres C",
        "Clear",
        "Blk",
        "FA",
        "Fls",
        "Svt",
        "Svp",
        "Svh",
        # Calculées
        "Tackles Failed",
        "Tackles Failed/90",
        "Poss+-/90",
        "Total Saves",
        "Saves/90",
        "Shots on Target Against",
        "Shots on Target Against/90",
        "Conc/90",
        "Defensive Actions/90",  # SCORE_COL
    }
)

# Neutres : × Modifier uniquement
NEU_COLS: frozenset = frozenset(
    {
        # CSV
        "Av Rat",
        "Distance/90",
        "xG/shot",
        "PoM",
        "K Hdrs/90",
        # Calculées
        "Non pen xG/Shot",
        "Non pen goals/Shot",
        "Conversion %",
        "Assists/CCC",
        "Pass Completion %",
        "Progressive Pass Rate",
        "Key Pass %",
        "Open Play Key Pass %",
        "Crosses Completed %",
        "Open Play Cross Completion %",
        "Clear Cut Chances %",
        "Tackle Completion %",
        "Key Tackles %",
        "Tackle Quality",
        "Headers Lost %",
        "Key Headers %",
        "Duels Win %",
        "Poss+-%",
        "xSave % Overperformance",
        "Saves/Goal Conceded",
        "Save Quality",
        "Clean Sheet Ratio",
    }
)


# ── Formule DAX exacte ───────────────────────────────────────────
def defensive_actions_90(row: pd.Series) -> float:
    """
    (Clear + Itc + Shts Blckd + Pres C + Tck W + K Tck*10
     + 0.8*Hdrs + 8*(K Hdrs/90 * Mins/90)) * 90 / Mins
    """
    mins = row.get("Mins", 0)
    if not mins or pd.isna(mins) or mins == 0:
        return 0.0
    return (
        (
            row.get("Clear", 0)
            + row.get("Itc", 0)
            + row.get("Shts Blckd", 0)
            + row.get("Pres C", 0)
            + row.get("Tck W", 0)
            + row.get("K Tck", 0) * 10
            + 0.8 * row.get("Hdrs", 0)
            + 8 * (row.get("K Hdrs/90", 0) * mins / 90)
        )
        * 90
        / mins
    )


# ── Ajustement Modifier / Possession sur les stats /90 ───────────
def apply_adjustments(
    df: pd.DataFrame,
    adj_df: pd.DataFrame,
    ligue_mod: dict,
) -> pd.DataFrame:
    """
    Applique par club les trois transformations Power Query :
      Offensive : × Modifier × (0.5 / Possession)
      Défensive : × Modifier × (Possession / 0.5)
      Neutre    : × Modifier
    ligue_mod : {ligue: modificateur}
    """
    df = df.copy()
    if "Club" not in df.columns:
        return df
    for _, adj_row in adj_df.iterrows():
        club = adj_row["Club"]
        ligue = adj_row.get("Ligue", "")
        mod = float(ligue_mod.get(ligue, 1.0))
        poss = float(adj_row["Possession"])
        if poss <= 0:
            poss = 0.5
        f_off = mod * (0.5 / poss)
        f_def = mod * (poss / 0.5)
        f_neu = mod
        if (
            abs(f_off - 1.0) < 1e-6
            and abs(f_def - 1.0) < 1e-6
            and abs(f_neu - 1.0) < 1e-6
        ):
            continue
        mask = df["Club"] == club
        for col in OFF_COLS:
            if col in df.columns and abs(f_off - 1.0) >= 1e-6:
                df.loc[mask, col] = df.loc[mask, col] * f_off
        for col in DEF_COLS:
            if col in df.columns and abs(f_def - 1.0) >= 1e-6:
                df.loc[mask, col] = df.loc[mask, col] * f_def
        for col in NEU_COLS:
            if col in df.columns and abs(f_neu - 1.0) >= 1e-6:
                df.loc[mask, col] = df.loc[mask, col] * f_neu
    return df


# ── Parsing position ─────────────────────────────────────────────
def parse_position(pos_str: str) -> frozenset:
    """
    Retourne un frozenset de tuples (position, côté_ou_None).

    Chaque groupe séparé par une virgule génère toutes les combinaisons
    poste × côté explicitement mentionnés.

    Exemples :
      'GK'              → {('GK', None)}
      'ST (C)'          → {('ST', 'C')}
      'DM'              → {('DM', None)}
      'D/WB (L)'        → {('D', 'L'), ('WB', 'L')}
      'M/AM (RL)'       → {('M','R'),('M','L'),('AM','R'),('AM','L')}
      'D (C), AM (RL)'  → {('D','C'),('AM','R'),('AM','L')}
    """
    if not isinstance(pos_str, str):
        return frozenset()
    combos: set = set()
    for group in pos_str.split(", "):
        group = group.strip()
        if not group:
            continue
        if "(" in group and group.endswith(")"):
            idx = group.index("(")
            pos_part = group[:idx].strip()
            sides = [ch for ch in group[idx + 1 : -1] if ch in ("R", "L", "C")]
            for pos in pos_part.split("/"):
                pos = pos.strip()
                if pos:
                    for side in sides:
                        combos.add((pos, side))
        else:
            for pos in group.split("/"):
                pos = pos.strip()
                if pos:
                    combos.add((pos, None))
    return frozenset(combos)


# ── Colonnes calculées (portées depuis Power Query) ─────────────
def _add_calculated_cols(df: pd.DataFrame) -> pd.DataFrame:
    def _c(name: str) -> pd.Series:
        return df[name] if name in df.columns else pd.Series(0.0, index=df.index)

    def _safe(num: pd.Series, den: pd.Series) -> pd.Series:
        return num / den.replace(0, np.nan)

    # Goals
    df["xg Overperformance"] = _c("Gls") - _c("xG")
    df["xg Overperformance/90"] = _safe(df["xg Overperformance"] * 90, _c("Mins"))
    df["Non pen goals"] = _c("Gls") - _c("Pens S")
    df["Non pen goals/90"] = _safe(df["Non pen goals"] * 90, _c("Mins"))
    df["Non pen goals/Shot"] = _safe(df["Non pen goals"], _c("Shots"))
    df["Minutes/Non pen goal"] = _safe(_c("Mins"), df["Non pen goals"])
    df["Non-pen Goals - Non-pen xG/90"] = df["Non pen goals/90"] - _c("NP-xG/90")
    df["Non pen xG/Shot"] = _safe(_c("NP-xG"), _c("Shots"))
    df["Non pen xG Overperformance"] = df["Non pen goals"] - _c("NP-xG")
    df["Non pen xG Overperformance/90"] = _safe(
        df["Non pen xG Overperformance"], _c("Mins")
    )
    df["Conversion %"] = _safe(_c("Gls"), _c("Shots"))
    df["Shot on target ratio"] = _safe(_c("ShT"), _c("Shots"))
    df["Shot quality"] = _safe(_c("xG"), _c("Shots"))
    df["Non pen goals/xG"] = _safe(_c("Non pen goals"), _c("NP-xG"))

    # Assists
    df["xA Overperformance"] = _c("Ast") - _c("xA")
    df["xA Overperformance/90"] = _safe(df["xA Overperformance"] * 90, _c("Mins"))
    df["Assists/CCC"] = _safe(_c("Ast"), _c("CCC"))

    # Goal Contributions
    df["Goal Contributions"] = _c("Gls") + _c("Ast")
    df["Goal Contributions/90"] = _safe(df["Goal Contributions"] * 90, _c("Mins"))
    df["xGC"] = _c("xG") + _c("xA")
    df["xGC/90"] = _safe(df["xGC"], _c("Mins"))
    df["xGC Overperformance"] = df["Goal Contributions"] - df["xGC"]
    df["xGC Overperformance/90"] = _safe(df["xGC Overperformance"] * 90, _c("Mins"))
    df["Non-pen GC"] = df["Non pen goals"] + _c("Ast")
    df["Non-pen GC/90"] = _safe(df["Non-pen GC"] * 90, _c("Mins"))
    df["Non-pen xGC"] = _c("NP-xG") + _c("xA")
    df["Non-pen xGC Overperformance"] = df["Non-pen GC"] - df["Non-pen xGC"]
    df["Non-pen xGC Overperformance/90"] = _safe(
        df["Non-pen xGC Overperformance"] * 90, _c("Mins")
    )

    # Passing
    df["Pass Completion %"] = _safe(_c("Ps C"), _c("Pas A"))
    df["Progressive Pass Rate"] = _safe(_c("Pr Passes"), _c("Pas A"))
    df["Key Pass %"] = _safe(_c("K Pas"), _c("Pas A"))
    df["Open Play Key Pass %"] = _safe(_c("OP-KP"), _c("Pas A"))
    df["Crosses Completed %"] = _safe(_c("Cr C"), _c("Cr A"))
    df["Open Play Crosses Attempted/90"] = _safe(_c("OP-Crs A") * 90, _c("Mins"))
    df["Open Play Crosses Completed/90"] = _safe(_c("OP-Crs C") * 90, _c("Mins"))
    df["Open Play Cross Completion %"] = _safe(_c("OP-Crs C"), _c("OP-Crs A"))
    df["Clear Cut Chances %"] = _safe(_c("CCC"), _c("Cr C"))
    df["Clear Cut Chances/90"] = _safe(_c("CCC") * 90, _c("Mins"))

    # Defending
    df["Tackles Failed"] = _c("Tck A") - _c("Tck W")
    df["Tackle Completion %"] = _safe(_c("Tck W"), _c("Tck A"))
    df["Tackles Failed/90"] = _safe(df["Tackles Failed"], _c("Mins"))
    df["Key Tackles %"] = _safe(_c("K Tck"), _c("Tck W"))
    df["Tackle Quality"] = _safe(_c("Tck W"), _c("Fls"))
    df["Headers Lost %"] = _safe(_c("Hdrs A") - _c("Hdrs"), _c("Hdrs A"))
    df["Key Headers %"] = _safe(_c("K Hdrs/90") * _c("Mins") / 90, _c("Hdrs"))
    df["Duels Win %"] = _safe(_c("Hdrs") + _c("Tck W"), _c("Hdrs A") + _c("Tck A"))

    # Pressing
    df["Poss+-/90"] = _c("Poss Won/90") - _c("Poss Lost/90")
    df["Poss+-%"] = _safe(_c("Poss Won/90"), _c("Poss Lost/90"))

    # Goalkeeping
    df["Total Saves"] = _c("Svt") + _c("Svp") + _c("Svh")
    df["Saves/90"] = _safe(df["Total Saves"] * 90, _c("Mins"))
    df["Saves/Goal Conceded"] = _safe(df["Total Saves"], _c("Conc"))
    df["Save Quality"] = _safe(
        3 * _c("Svh") + 2 * _c("Svt") + _c("Svp"), df["Total Saves"]
    )
    df["Shots on Target Against"] = df["Total Saves"] + _c("Conc")
    df["Shots on Target Against/90"] = _safe(
        df["Shots on Target Against"] * 90, _c("Mins")
    )
    df["Sv %"] = _safe(df["Total Saves"], df["Shots on Target Against"])
    df["xSave % Overperformance"] = _c("xSv %") - df["Sv %"]
    df["Conc/90"] = _safe(_c("Conc") * 90, _c("Mins"))
    df["Clean Sheet Ratio"] = _safe(_c("Clean Sheets"), _c("Starts"))

    # Distance
    df["Dist/90"] = _safe(_c("Distance") * 90, _c("Mins"))

    # Composite
    df["Attacking Actions/90"] = _safe(
        (
            _c("Ast")
            + _c("CCC")
            + 0.8 * _c("OP-Crs C")
            + 0.8 * _c("Drb")
            + df["Non pen goals"]
            + _c("ShT")
        )
        * 90,
        _c("Mins"),
    )
    df["Creative Actions/90"] = _safe(
        (_c("Ast") + _c("CCC") + _c("OP-Crs C") + _c("OP-KP") + _c("Pr Passes")) * 90,
        _c("Mins"),
    )

    return df


# ── Chargement ───────────────────────────────────────────────────
def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.rename(columns={"HdrsW/90": "Hdrs W/90"}, inplace=True)

    # Sanitize colonnes avec suffixe "km"
    for _km_col in ("Distance", "Dist/90"):
        if _km_col in df.columns:
            df[_km_col] = (
                df[_km_col].astype(str).str.replace("km", "", regex=False).str.strip()
            )

    non_numeric = {
        "Dist/90",  # recalculé dans _add_calculated_cols
        "Name",
        "Position",
        "Club",
        "Division",
        "Nat",
        "2nd Nat",
        "Inf",
        "Height",
        "Weight",
        "Personality",
        "Media Handling",
        "Wage",
        "Transfer Value",
        "Asking Price",
        "Preferred Foot",
        "Apps",
        "Home-Grown Status",
    }
    for col in df.columns:
        if col not in non_numeric:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Position" in df.columns:
        df["_pos_combos"] = df["Position"].apply(parse_position)

    df[SCORE_COL] = df.apply(defensive_actions_90, axis=1)
    df = _add_calculated_cols(df)
    return df


@st.cache_data
def load_from_path(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=";", decimal=".", encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(
            path, sep=";", decimal=".", encoding="latin-1", low_memory=False
        )
    return _prepare(df)


def load_from_upload(f) -> pd.DataFrame:
    try:
        df = pd.read_csv(f, sep=";", decimal=".", encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        f.seek(0)
        df = pd.read_csv(f, sep=";", decimal=".", encoding="latin-1", low_memory=False)
    return _prepare(df)


# ── Normalisation & références ───────────────────────────────────
def compute_refs(
    pop: pd.DataFrame,
    cols: list,
    pct_mode: bool = False,
    score_col: str = SCORE_COL,
):
    refs = {}
    _sc = score_col if score_col in pop.columns else SCORE_COL
    _sc_series = pop[_sc].dropna()
    if _sc_series.empty:
        # Score col is all-NaN: fall back to first valid row
        best_idx = pop.index[0]
    else:
        best_idx = _sc_series.idxmax()
    for col in cols:
        if col not in pop.columns:
            refs[col] = {
                "min": 0,
                "max": 1,
                "mean": 0.5 if pct_mode else 0,
                "p95": 0.95 if pct_mode else 0,
                "best": 0,
            }
            continue
        if pct_mode:
            pct = pop[col].rank(pct=True)
            refs[col] = {
                "min": 0.0,
                "max": 1.0,
                "mean": 0.5,
                "p95": 0.95,
                "best": float(pct.loc[best_idx]),
            }
        else:
            min_v = pop[col].min()
            max_v = pop[col].max()
            rng = max_v - min_v if max_v != min_v else 1
            norm = (pop[col] - min_v) / rng
            refs[col] = {
                "min": min_v,
                "max": max_v,
                "mean": float(norm.mean()),
                "p95": float(norm.quantile(0.95)),
                "best": float(norm.loc[best_idx]),
            }
    return refs, pop.loc[best_idx, "Name"]


def player_values(
    row: pd.Series,
    pop: pd.DataFrame,
    refs: dict,
    cols: list,
    pct_mode: bool = False,
) -> np.ndarray:
    vals = []
    for col in cols:
        if col not in row.index:
            vals.append(0.5 if pct_mode else 0.0)
            continue
        v = float(row[col])
        if pct_mode:
            vals.append(float(np.clip((pop[col] <= v).mean(), 0, 1)))
        else:
            r = refs[col]
            rng = r["max"] - r["min"]
            vals.append(float(np.clip((v - r["min"]) / rng if rng != 0 else 0.0, 0, 1)))
    return np.array(vals)


# ── Radar ────────────────────────────────────────────────────────
def draw_radar(
    refs: dict, best_name: str, players: list, cols: list, labels: list
) -> plt.Figure:
    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]

    def close(a):
        return np.append(a, a[0])

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0f0f13")
    ax.set_facecolor("#0f0f13")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="#aaaaaa", size=8.5)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25", "50", "75", "100"], color="#444455", size=7)
    ax.yaxis.grid(color="#2a2a3a", linestyle="--", linewidth=0.6, alpha=0.8)
    ax.xaxis.grid(color="#2a2a3a", linestyle="-", linewidth=0.4, alpha=0.5)
    ax.spines["polar"].set_color("#2a2a3a")
    ax.set_ylim(0, 1)

    mean_v = np.array([refs[c]["mean"] for c in cols])
    p95_v = np.array([refs[c]["p95"] for c in cols])
    best_v = np.array([refs[c]["best"] for c in cols])

    ax.plot(angles, close(mean_v), color="#FFFFFF", lw=1.5, ls="--", label="Moyenne")
    ax.fill(angles, close(mean_v), color="#FFFFFF", alpha=0.08)
    ax.plot(angles, close(p95_v), color="#f0a500", lw=1.5, ls="--", label="P95")
    ax.fill(angles, close(p95_v), color="#f0a500", alpha=0.08)
    ax.plot(
        angles, close(best_v), color="#00bfff", lw=2, label=f"Meilleur — {best_name}"
    )
    ax.fill(angles, close(best_v), color="#00bfff", alpha=0.12)

    for i, p in enumerate(players):
        c = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        ax.plot(angles, close(p["values"]), color=c, lw=2.5, label=p["name"])
        ax.fill(angles, close(p["values"]), color=c, alpha=0.15)
        ax.scatter(angles[:-1], p["values"], color=c, s=30, zorder=5)

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.45, 1.15),
        facecolor="#16161e",
        edgecolor="#2a2a3a",
        labelcolor="#e0e0e0",
        fontsize=8.5,
        framealpha=0.95,
    )
    plt.tight_layout()
    return fig


# ── Scatter (Plotly — interactif) ────────────────────────────────
def draw_scatter(
    pop: pd.DataFrame,
    x_col: str,
    y_col: str,
    highlighted: list,
    pct_mode: bool = False,
    show_outliers: bool = False,
    outlier_k: float = 1.5,
) -> go.Figure:
    if pct_mode:
        x_data = pop[x_col].rank(pct=True).values * 100
        y_data = pop[y_col].rank(pct=True).values * 100
        x_label = f"Percentile · {x_col}"
        y_label = f"Percentile · {y_col}"
    else:
        x_data = pop[x_col].values.astype(float)
        y_data = pop[y_col].values.astype(float)
        x_label = x_col
        y_label = y_col

    names = pop["Name"].values if "Name" in pop.columns else np.full(len(pop), "")

    # ── Colonnes fixes dans le hover ──────────────────────────────
    _hov_rat = (
        pop["Av Rat"].fillna(0.0).values
        if "Av Rat" in pop.columns
        else np.zeros(len(pop))
    )
    _hov_mins = (
        pop["Mins"].fillna(0.0).values if "Mins" in pop.columns else np.zeros(len(pop))
    )
    _hov_apps = (
        pop["Apps"].fillna("—").astype(str).values
        if "Apps" in pop.columns
        else np.full(len(pop), "—")
    )
    _hov_tv = (
        pop["Transfer Value"].fillna("—").astype(str).values
        if "Transfer Value" in pop.columns
        else np.full(len(pop), "—")
    )
    _hov_pos = (
        pop["Position"].fillna("—").astype(str).values
        if "Position" in pop.columns
        else np.full(len(pop), "—")
    )
    _hov_age = (
        pop["Age"].fillna(0.0).values if "Age" in pop.columns else np.zeros(len(pop))
    )
    customdata = np.column_stack(
        [_hov_rat, _hov_mins, _hov_apps, _hov_tv, _hov_pos, _hov_age]
    )

    mask = np.isfinite(x_data) & np.isfinite(y_data)

    # ── Détection outliers (IQR bivarié) ─────────────────────────
    if show_outliers and mask.sum() >= 4:

        def _iqr_outlier(v: np.ndarray, k: float) -> np.ndarray:
            finite = v[np.isfinite(v)]
            q1, q3 = np.percentile(finite, [25, 75])
            iqr = q3 - q1
            return (v < q1 - k * iqr) | (v > q3 + k * iqr)

        outlier_mask = mask & (
            _iqr_outlier(x_data, outlier_k) | _iqr_outlier(y_data, outlier_k)
        )
        normal_mask = mask & ~outlier_mask
    else:
        outlier_mask = np.zeros(len(mask), dtype=bool)
        normal_mask = mask

    fig = go.Figure()

    hover_tmpl = (
        "<b>%{text}</b><br>"
        + x_label
        + ": %{x:.2f}<br>"
        + y_label
        + ": %{y:.2f}<br>"
        + "Note: %{customdata[0]:.2f}<br>"
        + "Mins: %{customdata[1]:.0f}<br>"
        + "Apps: %{customdata[2]}<br>"
        + "Valeur transfert: %{customdata[3]}<br>"
        + "Position: %{customdata[4]}<br>"
        + "Âge: %{customdata[5]:.0f}<extra></extra>"
    )

    # Population normale
    fig.add_trace(
        go.Scatter(
            x=x_data[normal_mask],
            y=y_data[normal_mask],
            mode="markers",
            marker=dict(color="#6c7ab8", size=5, opacity=0.75),
            text=names[normal_mask],
            customdata=customdata[normal_mask],
            hovertemplate=hover_tmpl,
            name="Population",
            showlegend=False,
        )
    )

    # Outliers
    if show_outliers and outlier_mask.sum() > 0:
        fig.add_trace(
            go.Scatter(
                x=x_data[outlier_mask],
                y=y_data[outlier_mask],
                mode="markers+text",
                marker=dict(
                    color="#f0a500",
                    size=8,
                    opacity=0.9,
                    symbol="diamond",
                    line=dict(color="#ffffff", width=0.8),
                ),
                text=names[outlier_mask],
                customdata=customdata[outlier_mask],
                textposition="top center",
                textfont=dict(color="#f0a500", size=8),
                hovertemplate=hover_tmpl,
                name=f"Outliers ({outlier_mask.sum()})",
            )
        )

    # Trend line (exclut les outliers pour une régression robuste)
    trend_mask = normal_mask if show_outliers and outlier_mask.sum() > 0 else mask
    if trend_mask.sum() >= 2:
        coeffs = np.polyfit(x_data[trend_mask], y_data[trend_mask], 1)
        x_line = np.linspace(x_data[trend_mask].min(), x_data[trend_mask].max(), 300)
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=np.polyval(coeffs, x_line),
                mode="lines",
                line=dict(color="#f0a500", width=2, dash="dash"),
                name="Tendance",
                hoverinfo="skip",
            )
        )

    # Median lines
    med_x = float(np.median(x_data[mask]))
    med_y = float(np.median(y_data[mask]))
    fig.add_vline(
        x=med_x,
        line_color="#6666cc",
        line_width=1.5,
        line_dash="dot",
        annotation_text=f"Méd. X: {med_x:.1f}",
        annotation_font_color="#6666cc",
        annotation_position="top right",
    )
    fig.add_hline(
        y=med_y,
        line_color="#cc6666",
        line_width=1.5,
        line_dash="dot",
        annotation_text=f"Méd. Y: {med_y:.1f}",
        annotation_font_color="#cc6666",
        annotation_position="right",
    )

    # Highlighted players
    for i, p in enumerate(highlighted):
        rows = pop[pop["Name"] == p["name"]]
        if rows.empty:
            continue
        raw_px = float(rows[x_col].mean())
        raw_py = float(rows[y_col].mean())
        if pct_mode:
            px = float((pop[x_col] <= raw_px).mean()) * 100
            py = float((pop[y_col] <= raw_py).mean()) * 100
        else:
            px, py = raw_px, raw_py
        c = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        _p_rat = float(rows["Av Rat"].mean()) if "Av Rat" in rows.columns else 0.0
        _p_mins = float(rows["Mins"].mean()) if "Mins" in rows.columns else 0.0
        _p_apps = str(rows["Apps"].iloc[0]) if "Apps" in rows.columns else "—"
        _p_tv = (
            str(rows["Transfer Value"].iloc[0])
            if "Transfer Value" in rows.columns
            else "—"
        )
        _p_pos = str(rows["Position"].iloc[0]) if "Position" in rows.columns else "—"
        _p_age = float(rows["Age"].mean()) if "Age" in rows.columns else 0.0
        fig.add_trace(
            go.Scatter(
                x=[px],
                y=[py],
                mode="markers+text",
                marker=dict(color=c, size=12, line=dict(color="white", width=1.5)),
                text=[p["name"]],
                customdata=[[_p_rat, _p_mins, _p_apps, _p_tv, _p_pos, _p_age]],
                textposition="top right",
                textfont=dict(color=c, size=10),
                name=p["name"],
                hovertemplate=(
                    f"<b>{p['name']}</b><br>"
                    + x_label
                    + ": %{x:.2f}<br>"
                    + y_label
                    + ": %{y:.2f}<br>"
                    + "Note: %{customdata[0]:.2f}<br>"
                    + "Mins: %{customdata[1]:.0f}<br>"
                    + "Apps: %{customdata[2]}<br>"
                    + "Valeur transfert: %{customdata[3]}<br>"
                    + "Position: %{customdata[4]}<br>"
                    + "Âge: %{customdata[5]:.0f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        plot_bgcolor="#1a1a28",
        paper_bgcolor="#0f0f13",
        font=dict(color="#e0e0e0"),
        xaxis=dict(title=x_label, gridcolor="#2a2a3a", zerolinecolor="#2a2a3a"),
        yaxis=dict(title=y_label, gridcolor="#2a2a3a", zerolinecolor="#2a2a3a"),
        legend=dict(
            bgcolor="#16161e", bordercolor="#2a2a3a", font=dict(color="#e0e0e0")
        ),
        hoverlabel=dict(bgcolor="#16161e", bordercolor="#2a2a3a", font_color="#e0e0e0"),
        height=550,
        margin=dict(l=40, r=40, t=30, b=40),
    )
    return fig


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        "<h2 style='font-size:1.3rem'>⚙️ Configuration</h2>", unsafe_allow_html=True
    )

    # Source
    st.markdown(
        "<div class='section-title'>Source de données</div>", unsafe_allow_html=True
    )
    _out_dir = os.path.join(os.path.dirname(_SCRIPT_DIR), "output_files")
    _csv_files = (
        [
            os.path.join(_out_dir, f)
            for f in os.listdir(_out_dir)
            if f.lower().endswith(".csv")
        ]
        if os.path.isdir(_out_dir)
        else []
    )
    default_path = max(_csv_files, key=os.path.getmtime) if _csv_files else ""
    csv_path = st.text_input("Chemin du fichier CSV", value=default_path)
    uploaded = st.file_uploader("… ou importer un fichier", type=["csv"])

    df_raw = None
    if uploaded is not None:
        try:
            df_raw = load_from_upload(uploaded)
            st.success(f"{len(df_raw)} joueurs chargés")
        except Exception as e:
            st.error(f"Erreur chargement : {e}")
    elif os.path.exists(csv_path):
        try:
            df_raw = load_from_path(csv_path)
            st.success(f"{len(df_raw)} joueurs chargés")
        except Exception as e:
            st.error(f"Erreur chargement : {e}")
    else:
        st.info("Indique le chemin du CSV ou importe un fichier.")

    if df_raw is None:
        st.stop()

    # ── Session state : ajustements par club ─────────────────────
    _clubs_in_data = (
        sorted(df_raw["Club"].dropna().unique().tolist())
        if "Club" in df_raw.columns
        else []
    )

    def _default_adj_df(clubs: list) -> pd.DataFrame:
        div_map: dict = {}
        if "Division" in df_raw.columns:
            div_map = df_raw.groupby("Club")["Division"].first().to_dict()
        return pd.DataFrame(
            {
                "Club": clubs,
                "Ligue": [div_map.get(c, "") for c in clubs],
                "Possession": [0.5] * len(clubs),
            }
        )

    if "adj_df" not in st.session_state:
        _adj_df_init = _default_adj_df(_clubs_in_data)
        _club_settings, _ligue_mod_saved = _load_adj_settings()
        for _club, _rec in _club_settings.items():
            _m = _adj_df_init["Club"] == _club
            if _m.any():
                _adj_df_init.loc[_m, "Possession"] = float(_rec.get("Possession", 0.5))
        st.session_state.adj_df = _adj_df_init
        st.session_state.ligue_mod = _ligue_mod_saved
    else:
        _existing = set(st.session_state.adj_df["Club"].tolist())
        _new_clubs = [c for c in _clubs_in_data if c not in _existing]
        if _new_clubs:
            _div_map = (
                df_raw.groupby("Club")["Division"].first().to_dict()
                if "Division" in df_raw.columns
                else {}
            )
            _new_rows = pd.DataFrame(
                {
                    "Club": _new_clubs,
                    "Ligue": [_div_map.get(c, "") for c in _new_clubs],
                    "Possession": [0.5] * len(_new_clubs),
                }
            )
            st.session_state.adj_df = pd.concat(
                [st.session_state.adj_df, _new_rows], ignore_index=True
            )
        if "ligue_mod" not in st.session_state:
            _, st.session_state.ligue_mod = _load_adj_settings()

    # Cache df_adj — ne recalculer que si les ajustements changent
    _csv_key = (
        csv_path
        if uploaded is None
        else getattr(uploaded, "name", "") + str(getattr(uploaded, "size", 0))
    )
    _adj_sig = (
        _csv_key,
        int(pd.util.hash_pandas_object(st.session_state.adj_df).sum()),
        hash(frozenset(st.session_state.ligue_mod.items())),
    )
    if "df_adj" not in st.session_state or st.session_state.get("_adj_sig") != _adj_sig:
        st.session_state.df_adj = apply_adjustments(
            df_raw, st.session_state.adj_df, st.session_state.ligue_mod
        )
        st.session_state._adj_sig = _adj_sig
    df_adj = st.session_state.df_adj

    # ── Filtres ──────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>Filtres population</div>", unsafe_allow_html=True
    )

    # ── Sélecteur de position visuel ─────────────────────────────
    st.markdown("<div class='section-title'>Poste</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        div[data-testid="stSidebar"] button {
            padding: 2px 2px !important;
            font-size: 11px !important;
            min-height: 26px !important;
            line-height: 1.1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "pos_filter_mode" not in st.session_state:
        st.session_state["pos_filter_mode"] = "OU"
    if "pos_sel_combos" not in st.session_state:
        st.session_state["pos_sel_combos"] = set()

    _pm1, _pm2, _pm3 = st.columns(3)
    with _pm1:
        if st.button(
            "OU",
            key="btn_pos_or",
            type="primary"
            if st.session_state["pos_filter_mode"] == "OU"
            else "secondary",
            use_container_width=True,
        ):
            st.session_state["pos_filter_mode"] = "OU"
            st.rerun()
    with _pm2:
        if st.button(
            "ET",
            key="btn_pos_and",
            type="primary"
            if st.session_state["pos_filter_mode"] == "ET"
            else "secondary",
            use_container_width=True,
        ):
            st.session_state["pos_filter_mode"] = "ET"
            st.rerun()
    with _pm3:
        if st.button("✕ Reset", key="btn_pos_reset", use_container_width=True):
            st.session_state["pos_sel_combos"] = set()
            st.rerun()

    # Grille : None = case vide non cliquable
    _POS_GRID = [
        [None, ("ST", "C"), None],
        [("AM", "L"), ("AM", "C"), ("AM", "R")],
        [("M", "L"), ("M", "C"), ("M", "R")],
        [("WB", "L"), ("DM", None), ("WB", "R")],
        [("D", "L"), ("D", "C"), ("D", "R")],
        [None, ("GK", None), None],
    ]
    _POS_ROW_LABELS = ["ST", "AM", "M", "WB/DM", "D", "GK"]

    def _pos_lbl(pos, side):
        return pos if side is None else f"{pos}({side})"

    for _ri, _row in enumerate(_POS_GRID):
        _rc = st.columns([0.7, 1, 1, 1])
        with _rc[0]:
            st.markdown(
                f"<div style='font-size:10px;color:#666;text-align:right;"
                f"margin-top:6px;padding-right:4px'>{_POS_ROW_LABELS[_ri]}</div>",
                unsafe_allow_html=True,
            )
        for _ci, _cell in enumerate(_row):
            with _rc[_ci + 1]:
                if _cell is None:
                    st.markdown(" ")
                else:
                    _is_sel = _cell in st.session_state["pos_sel_combos"]
                    if st.button(
                        _pos_lbl(*_cell),
                        key=f"posbtn_{_cell[0]}_{_cell[1]}",
                        type="primary" if _is_sel else "secondary",
                        use_container_width=True,
                    ):
                        if _is_sel:
                            st.session_state["pos_sel_combos"].discard(_cell)
                        else:
                            st.session_state["pos_sel_combos"].add(_cell)
                        st.rerun()
    min_mins = st.slider(
        "Minutes minimum",
        0,
        int(df_raw["Mins"].max()) if "Mins" in df_raw.columns else 90,
        90,
        step=90,
    )

    # ── Filtres avancés ──────────────────────────────────────────
    _pct_mode_now = st.session_state.get("pct_mode", False)
    _SKIP_FILTER = {
        "UID",
        "Name",
        "Club",
        "Division",
        "Nat",
        "Position",
        "_pos_combos",
    }
    _filter_candidates = [
        c
        for c in df_adj.select_dtypes(include="number").columns
        if c not in _SKIP_FILTER
    ]

    with st.expander("🔍 Filtres avancés", expanded=False):
        _sel_filter_cols = st.multiselect(
            "Colonnes à filtrer",
            options=_filter_candidates,
            default=[],
            key="adv_filter_cols",
        )

        # ── Callbacks factory (évite le problème de fermeture en boucle) ──
        def _make_text_cb(s_key, lo_key, hi_key, s_min, s_max):
            def _cb():
                try:
                    lo = float(st.session_state[lo_key])
                    lo = max(s_min, min(s_max, lo))
                except (ValueError, TypeError):
                    lo = st.session_state[s_key][0]
                try:
                    hi = float(st.session_state[hi_key])
                    hi = max(s_min, min(s_max, hi))
                except (ValueError, TypeError):
                    hi = st.session_state[s_key][1]
                st.session_state[s_key] = (min(lo, hi), max(lo, hi))

            return _cb

        def _make_slider_cb(s_key, lo_key, hi_key):
            def _cb():
                lo, hi = st.session_state[s_key]
                st.session_state[lo_key] = f"{lo:.6g}"
                st.session_state[hi_key] = f"{hi:.6g}"

            return _cb

        _adv_filters: dict = {}
        for _fc in _sel_filter_cols:
            _is_age = _fc.lower() == "age"
            _use_pct = _pct_mode_now and not _is_age
            if _use_pct:
                _s_min, _s_max, _s_step = 0.0, 100.0, 1.0
            else:
                _col_vals = df_adj[_fc].dropna()
                _s_min = float(_col_vals.min())
                _s_max = float(_col_vals.max())
                _s_step = max((_s_max - _s_min) / 200, 0.01)

            _s_key = f"adv_{_fc}"
            _lo_key = f"adv_lo_{_fc}"
            _hi_key = f"adv_hi_{_fc}"

            # Initialise slider key if missing or out of range
            if _s_key not in st.session_state:
                st.session_state[_s_key] = (_s_min, _s_max)
            else:
                _sv = st.session_state[_s_key]
                st.session_state[_s_key] = (
                    max(_s_min, min(_s_max, _sv[0])),
                    max(_s_min, min(_s_max, _sv[1])),
                )

            _cur_lo, _cur_hi = st.session_state[_s_key]

            # Initialise text keys from slider if missing
            if _lo_key not in st.session_state:
                st.session_state[_lo_key] = f"{_cur_lo:.6g}"
            if _hi_key not in st.session_state:
                st.session_state[_hi_key] = f"{_cur_hi:.6g}"

            _text_cb = _make_text_cb(_s_key, _lo_key, _hi_key, _s_min, _s_max)
            _slider_cb = _make_slider_cb(_s_key, _lo_key, _hi_key)

            st.markdown(
                f"<span style='font-size:12px;color:#aaa;letter-spacing:.08em'>"
                f"{_fc}</span>",
                unsafe_allow_html=True,
            )
            _tc1, _tc2, _tc3 = st.columns([1, 4, 1])
            with _tc1:
                st.text_input(
                    "Min",
                    key=_lo_key,
                    on_change=_text_cb,
                    label_visibility="collapsed",
                )
            with _tc2:
                _lo, _hi = st.slider(
                    _fc,
                    _s_min,
                    _s_max,
                    key=_s_key,
                    step=float(f"{_s_step:.3g}"),
                    on_change=_slider_cb,
                    label_visibility="collapsed",
                )
            with _tc3:
                st.text_input(
                    "Max",
                    key=_hi_key,
                    on_change=_text_cb,
                    label_visibility="collapsed",
                )
            _adv_filters[_fc] = {"lo": _lo, "hi": _hi, "pct": _use_pct}

    # ── Sélection joueurs ────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>Joueurs à comparer</div>", unsafe_allow_html=True
    )

    pop = df_adj.copy()
    _sel_combos = st.session_state.get("pos_sel_combos", set())
    if _sel_combos and "_pos_combos" in pop.columns:
        _pos_mode = st.session_state.get("pos_filter_mode", "OU")
        if _pos_mode == "ET":
            pop = pop[pop["_pos_combos"].apply(lambda s: _sel_combos.issubset(s))]
        else:
            pop = pop[pop["_pos_combos"].apply(lambda s: bool(s & _sel_combos))]
    if "Mins" in pop.columns:
        pop = pop[pop["Mins"] >= min_mins]

    # Apply advanced filters
    for _fc, _fv in _adv_filters.items():
        if _fc not in pop.columns:
            continue
        if _fv["pct"]:
            _pct_series = pop[_fc].rank(pct=True) * 100
            pop = pop[(_pct_series >= _fv["lo"]) & (_pct_series <= _fv["hi"])]
        else:
            pop = pop[(pop[_fc] >= _fv["lo"]) & (pop[_fc] <= _fv["hi"])]

    if pop.empty:
        st.warning("Aucun joueur ne correspond aux filtres.")
        st.stop()

    # ── Application des colonnes personnalisées ──────────────────────
    if "custom_cols" not in st.session_state:
        st.session_state.custom_cols = _load_custom_cols()
    for _cc in st.session_state.custom_cols:
        _comp_cols = [
            _comp["col"] for _comp in _cc["components"] if _comp["col"] in pop.columns
        ]
        if _comp_cols:
            pop[_cc["name"]] = pd.concat(
                [pop[c].rank(pct=True) for c in _comp_cols], axis=1
            ).mean(axis=1)
        else:
            pop[_cc["name"]] = 0.0

    st.caption(f"{len(pop)} joueurs dans la population de référence")

    # Appliquer la sélection en attente (depuis le tableau) avant d'instancier le widget
    if "_pending_selected_names" in st.session_state:
        st.session_state["selected_names"] = st.session_state.pop(
            "_pending_selected_names"
        )

    player_options = sorted(pop["Name"].dropna().unique().tolist())
    selected_names = st.multiselect(
        "Sélectionner jusqu'à 5 joueurs",
        options=player_options,
        max_selections=5,
        key="selected_names",
    )


# ══════════════════════════════════════════════════════════════════
# CONTENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════
st.markdown(
    "<h1 style='font-size:2.2rem; margin-bottom:0'>⚽ Defensive Radar</h1>",
    unsafe_allow_html=True,
)

# ── Sélecteur de vue ─────────────────────────────────────────────
view_sel = st.selectbox(
    "Vue",
    options=["📊 Data", "⚽ Possession", "🔧 Modificateur", "🧮 Formules"],
    key="view_sel",
    label_visibility="collapsed",
)

# ══════════════════════════════════════════════════════════════════
# VUE POSSESSION
# ══════════════════════════════════════════════════════════════════
if view_sel == "⚽ Possession":
    st.markdown(
        "<div class='section-title'>Possession par club / ligue</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Possession moyenne de l'équipe (0.50 = 50 %). "
        "Utilisée pour normaliser les stats défensives /90."
    )
    edited_poss = st.data_editor(
        st.session_state.adj_df[["Club", "Possession"]].copy(),
        key="poss_editor",
        column_config={
            "Club": st.column_config.TextColumn("Club", disabled=True),
            "Possession": st.column_config.NumberColumn(
                "Possession", min_value=0.01, max_value=1.0, step=0.01, format="%.2f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )
    _poss_changed = (
        edited_poss["Possession"].round(4).tolist()
        != st.session_state.adj_df["Possession"].round(4).tolist()
    )
    _col_apply, _col_reset = st.columns([3, 1])
    with _col_apply:
        if st.button(
            "✅ Appliquer les possessions",
            key="btn_apply_poss",
            disabled=not _poss_changed,
        ):
            st.session_state.adj_df["Possession"] = edited_poss["Possession"].values
            _save_adj_settings(st.session_state.adj_df, st.session_state.ligue_mod)
            st.rerun()
    with _col_reset:
        if st.button("🔄 Reset", key="btn_reset_poss"):
            st.session_state.adj_df["Possession"] = 0.5
            _save_adj_settings(st.session_state.adj_df, st.session_state.ligue_mod)
            st.rerun()

# ══════════════════════════════════════════════════════════════════
# VUE MODIFICATEUR
# ══════════════════════════════════════════════════════════════════
elif view_sel == "🔧 Modificateur":
    st.markdown(
        "<div class='section-title'>Modificateur par ligue</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Facteur de difficulté par ligue (1.0 = neutre). "
        "Appliqué à tous les clubs de la ligue."
    )
    _all_ligues = sorted(st.session_state.adj_df["Ligue"].dropna().unique().tolist())
    _ligue_mod_df = pd.DataFrame(
        {
            "Ligue": _all_ligues,
            "Modificateur": [
                st.session_state.ligue_mod.get(lg, 1.0) for lg in _all_ligues
            ],
        }
    )
    edited_mod = st.data_editor(
        _ligue_mod_df.copy(),
        key="mod_editor",
        column_config={
            "Ligue": st.column_config.TextColumn("Ligue", disabled=True),
            "Modificateur": st.column_config.NumberColumn(
                "Modificateur", min_value=0.1, max_value=10.0, step=0.05, format="%.2f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )
    _new_mod_map = dict(zip(edited_mod["Ligue"], edited_mod["Modificateur"].round(4)))
    _old_mod_map = dict(
        zip(_ligue_mod_df["Ligue"], _ligue_mod_df["Modificateur"].round(4))
    )
    _mod_changed = _new_mod_map != _old_mod_map
    if st.button(
        "✅ Appliquer les modificateurs", key="btn_apply_mod", disabled=not _mod_changed
    ):
        st.session_state.ligue_mod = {lg: float(v) for lg, v in _new_mod_map.items()}
        _save_adj_settings(st.session_state.adj_df, st.session_state.ligue_mod)
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# VUE FORMULES
# ══════════════════════════════════════════════════════════════════
elif view_sel == "🧮 Formules":
    if "custom_cols" not in st.session_state:
        st.session_state.custom_cols = _load_custom_cols()

    st.markdown(
        "<div class='section-title'>Colonnes personnalisées</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Choisissez plusieurs statistiques pour créer votre propre score. "
        "Le score final est la moyenne des percentiles de chaque statistique sélectionnée. "
        "Les colonnes créées sont disponibles dans le radar et le scatter."
    )

    # ── Formules existantes ──────────────────────────────────────────
    if st.session_state.custom_cols:
        st.markdown(
            "<div class='section-title'>Formules existantes</div>",
            unsafe_allow_html=True,
        )
        _num_cols_for_edit = [
            c
            for c in pop.select_dtypes(include="number").columns
            if c not in {"UID", "_pos_combos"}
        ]
        for _i, _cc in enumerate(st.session_state.custom_cols):
            _editing_key = f"editing_cc_{_i}"
            _is_editing = st.session_state.get(_editing_key, False)
            with st.expander(f"**{_cc['name']}**", expanded=_is_editing):
                if not _is_editing:
                    _parts = [_c["col"] for _c in _cc["components"]]
                    st.markdown("  \n".join(_parts))
                    _btn_c1, _btn_c2 = st.columns(2)
                    with _btn_c1:
                        if st.button("✏️ Modifier", key=f"edit_cc_{_i}"):
                            st.session_state[_editing_key] = True
                            st.rerun()
                    with _btn_c2:
                        if st.button("🗑 Supprimer", key=f"del_cc_{_i}"):
                            st.session_state.custom_cols = [
                                c
                                for j, c in enumerate(st.session_state.custom_cols)
                                if j != _i
                            ]
                            _save_custom_cols(st.session_state.custom_cols)
                            st.rerun()
                else:
                    # ── Mode édition ─────────────────────────────────
                    _edit_name_key = f"edit_name_{_i}"
                    _edit_cols_key = f"edit_cols_{_i}"
                    # Initialise les valeurs si premier rendu en mode édition
                    if _edit_name_key not in st.session_state:
                        st.session_state[_edit_name_key] = _cc["name"]
                    if _edit_cols_key not in st.session_state:
                        st.session_state[_edit_cols_key] = [
                            c["col"]
                            for c in _cc["components"]
                            if c["col"] in _num_cols_for_edit
                        ]
                    _edit_name = st.text_input(
                        "Nom de la colonne",
                        key=_edit_name_key,
                    )
                    # Exclude other custom cols except this one
                    _edit_available = [
                        c
                        for c in _num_cols_for_edit
                        if c
                        not in [
                            _occ["name"]
                            for _j, _occ in enumerate(st.session_state.custom_cols)
                            if _j != _i
                        ]
                    ]
                    _edit_sel_cols = st.multiselect(
                        "Colonnes à combiner",
                        options=_edit_available,
                        key=_edit_cols_key,
                    )
                    _can_save = bool(_edit_name.strip()) and bool(_edit_sel_cols)
                    _save_c, _cancel_c = st.columns(2)
                    with _save_c:
                        if st.button(
                            "✅ Enregistrer",
                            key=f"save_cc_{_i}",
                            disabled=not _can_save,
                        ):
                            _updated_cc = {
                                "name": _edit_name.strip(),
                                "components": [{"col": c} for c in _edit_sel_cols],
                            }
                            _new_list = list(st.session_state.custom_cols)
                            _new_list[_i] = _updated_cc
                            st.session_state.custom_cols = _new_list
                            _save_custom_cols(st.session_state.custom_cols)
                            st.session_state[_editing_key] = False
                            # Clean up temp keys
                            for _k in [_edit_name_key, _edit_cols_key]:
                                st.session_state.pop(_k, None)
                            st.rerun()
                    with _cancel_c:
                        if st.button("✗ Annuler", key=f"cancel_cc_{_i}"):
                            st.session_state[_editing_key] = False
                            for _k in [_edit_name_key, _edit_cols_key]:
                                st.session_state.pop(_k, None)
                            st.rerun()

    # ── Nouvelle formule ───────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>Nouvelle formule</div>",
        unsafe_allow_html=True,
    )
    _num_cols_for_formula = [
        c
        for c in pop.select_dtypes(include="number").columns
        if c not in {"UID", "_pos_combos"}
        and c not in [_cc["name"] for _cc in st.session_state.custom_cols]
    ]
    _formula_name = st.text_input(
        "Nom de la colonne",
        key="formula_name",
        placeholder="ex: Mon Score Offensif",
    )
    _formula_cols = st.multiselect(
        "Colonnes à combiner",
        options=_num_cols_for_formula,
        key="formula_cols",
    )
    _weights: dict = {}
    if _formula_cols:
        st.markdown("<div class='section-title'>Poids</div>", unsafe_allow_html=True)
        _fw_cols = st.columns(min(3, len(_formula_cols)))
        for _fi, _fc in enumerate(_formula_cols):
            with _fw_cols[_fi % len(_fw_cols)]:
                _weights[_fc] = st.number_input(
                    _fc,
                    value=1.0,
                    step=0.1,
                    format="%.3g",
                    key=f"fw_{_fc}",
                )

    _can_create = bool(_formula_name.strip()) and bool(_formula_cols)
    if st.button("✅ Créer la formule", disabled=not _can_create, key="btn_create_cc"):
        _new_cc = {
            "name": _formula_name.strip(),
            "components": [
                {"col": c, "weight": float(_weights[c])} for c in _formula_cols
            ],
        }
        st.session_state.custom_cols = [
            c for c in st.session_state.custom_cols if c["name"] != _new_cc["name"]
        ] + [_new_cc]
        _save_custom_cols(st.session_state.custom_cols)
        st.success(f"✓ '{_new_cc['name']}' créée")
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# VUE DATA
# ══════════════════════════════════════════════════════════════════
else:
    # ── Info bar ─────────────────────────────────────────────────
    _sel_combos_display = st.session_state.get("pos_sel_combos", set())
    if _sel_combos_display:
        _mode_lbl = st.session_state.get("pos_filter_mode", "OU")
        _combos_str = f" · Poste ({_mode_lbl}) : " + ", ".join(
            (p if s is None else f"{p}({s})") for p, s in sorted(_sel_combos_display)
        )
    else:
        _combos_str = ""
    pos_filter_str = _combos_str
    st.markdown(
        f"<p style='color:#555; font-size:13px; margin-top:4px'>"
        f"{len(pop)} joueurs · Ajustements par club{pos_filter_str}"
        f"</p>",
        unsafe_allow_html=True,
    )

    # ── Vérification colonnes ─────────────────────────────────────
    missing = [c for c in STATS_COLS if c not in pop.columns]
    if missing:
        st.error(f"Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    # ── Percentile toggle ─────────────────────────────────────────
    pct_mode = st.checkbox(
        "📐 Mode percentile (recalculé sur la population filtrée)",
        value=False,
        key="pct_mode",
    )

    # ── Données brutes des joueurs sélectionnés ───────────────────
    _num_cols = pop.select_dtypes(include="number").columns.tolist()
    base_players: list = []
    for name in selected_names:
        rows = pop[pop["Name"] == name]
        if rows.empty:
            st.warning(f"'{name}' introuvable dans la population filtrée.")
            continue
        row = rows[[c for c in _num_cols if c in rows.columns]].mean()
        base_players.append(
            {"name": name, "row": row, "score": float(rows[SCORE_COL].mean())}
        )

    chart_type = st.radio(
        "",
        ["📡 Radar", "📊 Scatter", "📋 Tableau"],
        horizontal=True,
        key="chart_type",
        label_visibility="collapsed",
    )

    # ══════════════════════════════════════════════════════════════
    # RADAR
    # ══════════════════════════════════════════════════════════════
    if chart_type == "📡 Radar":
        # ── Template formule ─────────────────────────────────────
        _radar_num_cols = [
            c
            for c in pop.select_dtypes(include="number").columns
            if c not in {"UID", "_pos_combos"}
        ]
        _formula_templates = [
            cc
            for cc in st.session_state.get("custom_cols", [])
            if cc["name"] in _radar_num_cols
        ]
        if _formula_templates:
            _tpl_names = ["— Aucun —"] + [cc["name"] for cc in _formula_templates]
            _tpl_c1, _tpl_c2 = st.columns([4, 1])
            with _tpl_c1:
                _chosen_tpl = st.selectbox(
                    "📋 Template formule",
                    options=_tpl_names,
                    key="radar_template",
                    help=(
                        "Applique une formule personnalisée : axes du radar = "
                        "composantes de la formule, métrique meilleur joueur = formule."
                    ),
                )
            with _tpl_c2:
                st.markdown(
                    "<div style='margin-top:26px'></div>", unsafe_allow_html=True
                )
                if st.button(
                    "Appliquer",
                    key="btn_apply_radar_tpl",
                    disabled=(_chosen_tpl == "— Aucun —"),
                ):
                    _tpl_cc = next(
                        cc for cc in _formula_templates if cc["name"] == _chosen_tpl
                    )
                    _tpl_comp_cols = [
                        c["col"]
                        for c in _tpl_cc["components"]
                        if c["col"] in pop.columns
                    ]
                    st.session_state.custom_radar_cols = _tpl_comp_cols
                    st.session_state.radar_score_col = _tpl_cc["name"]
                    st.rerun()

        radar_mode = "Custom"

        _available = [
            c
            for c in pop.select_dtypes(include="number").columns
            if c not in {"UID", "_pos_combos"}
        ]
        radar_cols = st.multiselect(
            "Statistiques du radar (3 à 12)",
            options=_available,
            key="custom_radar_cols",
        )
        radar_labels = [
            c.replace("/90", "\n/90") if len(c) > 9 else c for c in radar_cols
        ]
        _default_score_col = SCORE_COL

        _score_opts = [
            c
            for c in pop.select_dtypes(include="number").columns
            if c not in {"UID", "_pos_combos"}
        ]
        _score_default_idx = (
            _score_opts.index(_default_score_col)
            if _default_score_col in _score_opts
            else 0
        )
        radar_score_col = st.selectbox(
            "🏆 Métrique meilleur joueur",
            options=_score_opts,
            index=_score_default_idx,
            key="radar_score_col",
        )

        if len(radar_cols) < 3:
            st.warning("Sélectionne au moins 3 dimensions pour afficher le radar.")
        else:
            refs_r, best_name_r = compute_refs(
                pop, radar_cols, pct_mode, radar_score_col
            )

            radar_players: list = []
            for p in base_players:
                _rows = pop[pop["Name"] == p["name"]]
                _score = (
                    float(_rows[radar_score_col].mean())
                    if radar_score_col in _rows.columns and not _rows.empty
                    else p["score"]
                )
                radar_players.append(
                    {
                        "name": p["name"],
                        "values": player_values(
                            p["row"], pop, refs_r, radar_cols, pct_mode
                        ),
                        "raw": {
                            c: float(p["row"][c])
                            for c in radar_cols
                            if c in p["row"].index
                        },
                        "score": _score,
                    }
                )

            col_radar, col_stats = st.columns([2, 1])

            with col_radar:
                fig = draw_radar(
                    refs_r, best_name_r, radar_players, radar_cols, radar_labels
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            with col_stats:
                st.markdown(
                    "<div class='section-title'>Meilleur joueur</div>",
                    unsafe_allow_html=True,
                )
                best_row = pop.loc[pop[radar_score_col].idxmax()]
                club_html = (
                    f"<div class='metric-card'><div class='metric-label'>Club</div>"
                    f"<div class='metric-value' style='font-size:18px'>{best_row.get('Club', '—')}</div></div>"
                    if "Club" in best_row.index
                    else ""
                )
                st.markdown(
                    f"""
                    <div class='metric-card'>
                        <div class='metric-label'>Nom</div>
                        <div class='metric-value' style='font-size:20px'>{best_row["Name"]}</div>
                    </div>
                    <div class='metric-card'>
                        <div class='metric-label'>{radar_score_col}</div>
                        <div class='metric-value'>{best_row.get(radar_score_col, 0.0):.2f}</div>
                    </div>
                    {club_html}
                    """,
                    unsafe_allow_html=True,
                )

                if radar_players:
                    st.markdown(
                        "<div class='section-title'>"
                        + (
                            "Stats percentiles"
                            if pct_mode
                            else "Stats brutes (ajustées)"
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    for i, p in enumerate(radar_players):
                        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
                        st.markdown(
                            f"<span class='player-tag' style='background:{color}22; color:{color};"
                            f" border:1px solid {color}55'>{p['name']} — {p['score']:.2f}</span>",
                            unsafe_allow_html=True,
                        )
                        if pct_mode:
                            _display = {
                                c: f"{float((pop[c] <= p['raw'].get(c, 0)).mean()) * 100:.1f} %"
                                for c in radar_cols
                                if c in pop.columns
                            }
                        else:
                            _display = {
                                c: f"{p['raw'].get(c, 0):.2f}" for c in radar_cols
                            }
                        st.dataframe(
                            pd.DataFrame({"Valeur": _display}),
                            use_container_width=True,
                            height=min(280, 38 * len(radar_cols) + 38),
                        )

            if radar_players:
                st.markdown(
                    "<div class='section-title' style='margin-top:30px'>Tableau comparatif</div>",
                    unsafe_allow_html=True,
                )
                _extra_col = (
                    radar_score_col if radar_score_col not in radar_cols else None
                )
                if pct_mode:

                    def _pct_fmt(col, val):
                        if col not in pop.columns:
                            return "—"
                        return f"{float((pop[col] <= val).mean()) * 100:.1f} %"

                    cmp_rows = [
                        {
                            "Joueur": "— Moyenne",
                            **{c: "50.0 %" for c in radar_cols if c in pop.columns},
                            **(
                                {_extra_col: "50.0 %"}
                                if _extra_col and _extra_col in pop.columns
                                else {}
                            ),
                        },
                        {
                            "Joueur": "— P95",
                            **{c: "95.0 %" for c in radar_cols if c in pop.columns},
                            **(
                                {_extra_col: "95.0 %"}
                                if _extra_col and _extra_col in pop.columns
                                else {}
                            ),
                        },
                        {
                            "Joueur": f"⭐ {best_name_r}",
                            **{
                                c: _pct_fmt(c, best_row[c])
                                for c in radar_cols
                                if c in best_row.index
                            },
                            **(
                                {
                                    _extra_col: _pct_fmt(
                                        _extra_col, best_row.get(_extra_col, 0.0)
                                    )
                                }
                                if _extra_col
                                else {}
                            ),
                        },
                    ]
                    for p in radar_players:
                        cmp_rows.append(
                            {
                                "Joueur": p["name"],
                                **{
                                    c: _pct_fmt(c, p["raw"].get(c, 0))
                                    for c in radar_cols
                                },
                                **(
                                    {_extra_col: _pct_fmt(_extra_col, p["score"])}
                                    if _extra_col
                                    else {}
                                ),
                            }
                        )
                else:
                    cmp_rows = [
                        {
                            "Joueur": "— Moyenne",
                            **{
                                c: f"{pop[c].mean():.2f}"
                                for c in radar_cols
                                if c in pop.columns
                            },
                            **(
                                {_extra_col: f"{pop[_extra_col].mean():.2f}"}
                                if _extra_col and _extra_col in pop.columns
                                else {}
                            ),
                        },
                        {
                            "Joueur": "— P95",
                            **{
                                c: f"{pop[c].quantile(0.95):.2f}"
                                for c in radar_cols
                                if c in pop.columns
                            },
                            **(
                                {_extra_col: f"{pop[_extra_col].quantile(0.95):.2f}"}
                                if _extra_col and _extra_col in pop.columns
                                else {}
                            ),
                        },
                        {
                            "Joueur": f"⭐ {best_name_r}",
                            **{
                                c: f"{best_row[c]:.2f}"
                                for c in radar_cols
                                if c in best_row.index
                            },
                            **(
                                {_extra_col: f"{best_row.get(_extra_col, 0.0):.2f}"}
                                if _extra_col
                                else {}
                            ),
                        },
                    ]
                    for p in radar_players:
                        cmp_rows.append(
                            {
                                "Joueur": p["name"],
                                **{c: f"{p['raw'].get(c, 0):.2f}" for c in radar_cols},
                                **(
                                    {_extra_col: f"{p['score']:.2f}"}
                                    if _extra_col
                                    else {}
                                ),
                            }
                        )
                st.dataframe(
                    pd.DataFrame(cmp_rows).set_index("Joueur"),
                    use_container_width=True,
                )

            # ── Infos générales ──────────────────────────────────
            _info_cols = [
                c
                for c in [
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
                if c in pop.columns
            ]
            if _info_cols and radar_players:
                st.markdown(
                    "<div class='section-title' style='margin-top:30px'>Infos générales</div>",
                    unsafe_allow_html=True,
                )
                _info_rows = []
                # Meilleur joueur en premier
                _best_info_row = {
                    c: best_row[c] if c in best_row.index else "—" for c in _info_cols
                }
                _best_info_row["Name"] = f"⭐ {best_row['Name']}"
                _info_rows.append(_best_info_row)
                for _ip in radar_players:
                    _ip_rows = pop[pop["Name"] == _ip["name"]]
                    if _ip_rows.empty:
                        continue
                    _ip_row = _ip_rows.iloc[0]
                    _info_rows.append(
                        {
                            c: _ip_row[c] if c in _ip_row.index else "—"
                            for c in _info_cols
                        }
                    )
                if _info_rows:
                    st.dataframe(
                        pd.DataFrame(_info_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

    # ══════════════════════════════════════════════════════════════
    # SCATTER
    # ══════════════════════════════════════════════════════════════
    elif chart_type == "📊 Scatter":
        _exclude = {"UID", "_pos_combos", "Mins"}
        scatter_cols = [
            c for c in pop.select_dtypes(include="number").columns if c not in _exclude
        ]
        default_x_idx = (
            scatter_cols.index(STATS_COLS[0]) if STATS_COLS[0] in scatter_cols else 0
        )
        default_y_idx = (
            scatter_cols.index(SCORE_COL)
            if SCORE_COL in scatter_cols
            else min(1, len(scatter_cols) - 1)
        )

        sc1, sc2 = st.columns(2)
        with sc1:
            x_col = st.selectbox(
                "Axe X", options=scatter_cols, index=default_x_idx, key="scatter_x"
            )
        with sc2:
            y_col = st.selectbox(
                "Axe Y", options=scatter_cols, index=default_y_idx, key="scatter_y"
            )

        out_c1, out_c2 = st.columns([1, 2])
        with out_c1:
            show_outliers = st.checkbox(
                "🔍 Détecter les outliers", value=False, key="show_outliers"
            )
        with out_c2:
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

        fig_sc = draw_scatter(
            pop, x_col, y_col, base_players, pct_mode, show_outliers, outlier_k
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    # TABLEAU
    # ══════════════════════════════════════════════════════════════
    elif chart_type == "📋 Tableau":
        _tbl_num_cols = [
            c
            for c in pop.select_dtypes(include="number").columns
            if c not in {"UID", "_pos_combos"}
        ]

        # ── Template formule ──────────────────────────────────────
        _tbl_formula_templates = [
            cc
            for cc in st.session_state.get("custom_cols", [])
            if cc["name"] in _tbl_num_cols
        ]
        _tbl_active_formula: str | None = None
        if _tbl_formula_templates:
            _tbl_tpl_names = ["— Aucun —"] + [
                cc["name"] for cc in _tbl_formula_templates
            ]
            _ttc1, _ttc2 = st.columns([4, 1])
            with _ttc1:
                _tbl_chosen_tpl = st.selectbox(
                    "📋 Charger une formule",
                    options=_tbl_tpl_names,
                    key="tbl_template",
                )
            with _ttc2:
                st.markdown(
                    "<div style='margin-top:26px'></div>", unsafe_allow_html=True
                )
                if st.button(
                    "Appliquer",
                    key="btn_apply_tbl_tpl",
                    disabled=(_tbl_chosen_tpl == "— Aucun —"),
                ):
                    _tbl_cc = next(
                        cc
                        for cc in _tbl_formula_templates
                        if cc["name"] == _tbl_chosen_tpl
                    )
                    st.session_state.tbl_extra_cols = [
                        c["col"]
                        for c in _tbl_cc["components"]
                        if c["col"] in pop.columns
                    ]
                    st.session_state.tbl_active_formula = _tbl_cc["name"]
                    st.rerun()
            if _tbl_chosen_tpl != "— Aucun —":
                _tbl_active_formula = _tbl_chosen_tpl

        # ── Colonnes supplémentaires ──────────────────────────────
        if "tbl_extra_cols" not in st.session_state:
            st.session_state.tbl_extra_cols = []
        tbl_extra_cols = st.multiselect(
            "Colonnes supplémentaires",
            options=_tbl_num_cols,
            key="tbl_extra_cols",
        )

        _tbl_fixed = [
            c
            for c in [
                "Name",
                "Club",
                "Position",
                "Age",
                "Mins",
                "Apps",
                "Transfer Value",
            ]
            if c in pop.columns
        ]
        # Colonnes extra + formule elle-même si active
        _tbl_stat_cols = [c for c in tbl_extra_cols if c not in _tbl_fixed]
        if (
            _tbl_active_formula
            and _tbl_active_formula in pop.columns
            and _tbl_active_formula not in _tbl_stat_cols
        ):
            _tbl_stat_cols = [_tbl_active_formula] + _tbl_stat_cols
        _all_tbl_cols = _tbl_fixed + _tbl_stat_cols

        # ── Construire le dataframe affiché ───────────────────────
        _tbl_df = pop[[c for c in _all_tbl_cols if c in pop.columns]].copy()

        _pct_cols = [
            c
            for c in _tbl_stat_cols
            if c in pop.columns and pd.api.types.is_numeric_dtype(pop[c])
        ]
        if pct_mode:
            for _tc in _pct_cols:
                _tbl_df[_tc] = pop[_tc].rank(pct=True).mul(100).round(1)

        # ── Filtres du tableau (affichage uniquement) ──────────────
        _tbl_txt_filterable = [
            c
            for c in _all_tbl_cols
            if c in _tbl_df.columns and not pd.api.types.is_numeric_dtype(_tbl_df[c])
        ]
        _tbl_num_filterable = [
            c
            for c in _all_tbl_cols
            if c in _tbl_df.columns and pd.api.types.is_numeric_dtype(_tbl_df[c])
        ]

        with st.expander("🔍 Filtres du tableau", expanded=False):
            _tbl_name_q = st.text_input(
                "Recherche nom",
                key="tbl_name_search",
                placeholder="Contient…",
            )
            _ftbl_sel_cols = st.multiselect(
                "Autres colonnes à filtrer",
                options=_tbl_txt_filterable + _tbl_num_filterable,
                key="tbl_filter_cols_sel",
            )
            _tbl_col_filters: dict = {}
            for _fc in _ftbl_sel_cols:
                if pd.api.types.is_numeric_dtype(_tbl_df[_fc]):
                    _fc_min = float(_tbl_df[_fc].min())
                    _fc_max = float(_tbl_df[_fc].max())
                    _fcc1, _fcc2 = st.columns(2)
                    with _fcc1:
                        _flo = st.number_input(
                            f"{_fc} ≥",
                            value=_fc_min,
                            key=f"tbl_flo_{_fc}",
                        )
                    with _fcc2:
                        _fhi = st.number_input(
                            f"{_fc} ≤",
                            value=_fc_max,
                            key=f"tbl_fhi_{_fc}",
                        )
                    _tbl_col_filters[_fc] = ("num", _flo, _fhi)
                else:
                    _ftxt = st.text_input(
                        f"{_fc} contient",
                        key=f"tbl_ftxt_{_fc}",
                        placeholder="…",
                    )
                    _tbl_col_filters[_fc] = ("txt", _ftxt)

        # Appliquer les filtres sur une copie d'affichage
        _tbl_df_view = _tbl_df.copy()
        if _tbl_name_q:
            _tbl_df_view = (
                _tbl_df_view[
                    _tbl_df_view["Name"]
                    .astype(str)
                    .str.contains(_tbl_name_q, case=False, na=False)
                ]
                if "Name" in _tbl_df_view.columns
                else _tbl_df_view
            )
        for _fc, _fv in _tbl_col_filters.items():
            if _fc not in _tbl_df_view.columns:
                continue
            if _fv[0] == "num":
                _tbl_df_view = _tbl_df_view[
                    (_tbl_df_view[_fc] >= _fv[1]) & (_tbl_df_view[_fc] <= _fv[2])
                ]
            elif _fv[0] == "txt" and _fv[1]:
                _tbl_df_view = _tbl_df_view[
                    _tbl_df_view[_fc]
                    .astype(str)
                    .str.contains(_fv[1], case=False, na=False)
                ]

        # Réinitialiser la sélection de lignes si le filtre change
        _view_hash = hash(tuple(_tbl_df_view.index.tolist()))
        if st.session_state.get("_tbl_view_hash") != _view_hash:
            st.session_state["_tbl_row_sel"] = []
            st.session_state["_tbl_view_hash"] = _view_hash

        # ── Mise en évidence des joueurs sélectionnés ─────────────
        if "Name" in _tbl_df_view.columns:

            def _highlight_selected(row):
                color = (
                    "background-color: #fffde7; color: #1a1a1a"
                    if row.get("Name", "") in selected_names
                    else ""
                )
                return [color] * len(row)

            _styled_tbl = _tbl_df_view.style.apply(_highlight_selected, axis=1)
        else:
            _styled_tbl = _tbl_df_view

        _tbl_sel = st.dataframe(
            _styled_tbl,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            column_config={
                c: st.column_config.NumberColumn(c, format="%.1f %%")
                for c in _pct_cols
                if pct_mode
            },
        )
        st.caption(
            "Cliquez sur une ligne pour ajouter / retirer le joueur de la sélection."
        )

        # ── Sync clics tableau → selected_names ───────────────────
        if "Name" in _tbl_df_view.columns:
            _prev_tbl_sel = st.session_state.get("_tbl_row_sel", [])
            _curr_tbl_sel = _tbl_sel.selection.rows
            if sorted(_curr_tbl_sel) != sorted(_prev_tbl_sel):
                _prev_names = {
                    _tbl_df_view.iloc[i]["Name"]
                    for i in _prev_tbl_sel
                    if i < len(_tbl_df_view)
                }
                _curr_names = {
                    _tbl_df_view.iloc[i]["Name"]
                    for i in _curr_tbl_sel
                    if i < len(_tbl_df_view)
                }
                _new_sel = list(selected_names)
                for _n in _prev_names - _curr_names:
                    if _n in _new_sel:
                        _new_sel.remove(_n)
                for _n in _curr_names - _prev_names:
                    if _n not in _new_sel and len(_new_sel) < 5:
                        _new_sel.append(_n)
                st.session_state["_tbl_row_sel"] = _curr_tbl_sel
                if set(_new_sel) != set(selected_names):
                    st.session_state["_pending_selected_names"] = _new_sel
                    st.rerun()
            else:
                st.session_state["_tbl_row_sel"] = _curr_tbl_sel
