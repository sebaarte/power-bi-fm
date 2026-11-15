"""Lecture, fusion et préparation des exports CSV FM27."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
import streamlit as st

from moneyballer.config import EXPORT_DIR, SCORE_COL
from moneyballer.data.metrics import add_calculated_cols, defensive_actions_90
from moneyballer.data.positions import parse_position

# Export FM27 → noms utilisés par l'app
CSV_RENAME = {
    "HdrsW/90": "Hdrs W/90",
    "UniqueId": "UID",
    "Playerteam#1": "Name",
    "Nation of Birth": "Nat",
    "Minutes": "Mins",
    "Rating": "Av Rat",
    "Goals": "Gls",
    "Goals per 90 minutes": "Gls/90",
    "Assists": "Ast",
    "Goals Conceded": "Conc",
    "Fouls": "Fls",
    "Fouls Against": "FA",
    "Tck C": "Tck W",
    "Clearances": "Clear",
    "Key": "K Pas",
    "KP/90": "K Ps/90",
    "PsP": "Pr Passes",
    "MLG": "Gl Mst",
    "Shots From Outside The Box Per 90 minutes": "Shots Outside Box/90",
}
# Doublon d'ID + % arrondis à l'entier, recalculés dans add_calculated_cols
CSV_DROP = ["Unique ID", "Pas %", "Conv %", "Shot %", "OP-Cr %", "Tck R", "Cr C/A"]

NON_NUMERIC_COLS = frozenset(
    {
        "Dist/90",  # recalculé dans add_calculated_cols
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
        "Home-Grown Status",
    }
)
# Colonnes numériques qui décrivent le joueur sans être des statistiques
NUMERIC_ATTRIBUTE_COLS = frozenset({"UID", "Age"})

# Totaux additionnés lors de la fusion de deux lignes de même UID ; les autres
# stats (/90, %, note) sont moyennées pondérées par les minutes, ce qui revient
# à les recalculer sur les totaux additionnés.
TOTAL_COLS = frozenset(
    {
        "Mins",
        "Starts",
        "Apps",
        "Yel",
        "Red",
        "PoM",
        "Pens",
        "Pens S",
        "Pens Faced",
        "Pens Saved",
        "Gls",
        "Ast",
        "Conc",
        "Fls",
        "FA",
        "xG",
        "xG-OP",
        "NP-xG",
        "xA",
        "xGP",
        "Clean Sheets",
        "Hdrs",
        "Hdrs A",
        "Tck W",
        "Tck A",
        "K Tck",
        "Shots",
        "ShT",
        "Shts Blckd",
        "Goals From Outside The Box",
        "Svt",
        "Svh",
        "Svp",
        "Pr Passes",
        "Pres C",
        "Pres A",
        "Ps C",
        "Pas A",
        "K Pas",
        "OP-KP",
        "OP-Crs C",
        "OP-Crs A",
        "Cr C",
        "Cr A",
        "Off",
        "Gl Mst",
        "Itc",
        "Clear",
        "CCC",
        "Blk",
        "Drb",
        "Distance",
    }
)
# Ratios FM recalculés sur les totaux fusionnés : col → (numérateur, dénominateur, échelle)
RATIO_COLS = {
    "Mins/Gl": ("Mins", "Gls", 1),
    "xG/shot": ("xG", "Shots", 1),
    "Pen/R": ("Pens S", "Pens", 100),
    "Pens Saved Ratio": ("Pens Saved", "Pens Faced", 100),
}

_READ_OPTS = {"sep": ";", "decimal": ".", "low_memory": False}


def latest_export() -> str:
    """Chemin du CSV le plus récent du dossier d'export, ou chaîne vide."""
    if not EXPORT_DIR.is_dir():
        return ""
    files = [p for p in EXPORT_DIR.iterdir() if p.suffix.lower() == ".csv"]
    return str(max(files, key=lambda p: p.stat().st_mtime)) if files else ""


def _fmt_money(x: int) -> str:
    if x >= 1_000_000:
        return f"{round(x / 1_000_000, 2):g}M"
    if x >= 1_000:
        return f"{round(x / 1_000, 1):g}K"
    return str(x)


def _fmt_transfer_value(v) -> str:
    v = pd.to_numeric(v, errors="coerce")
    if pd.isna(v) or v < 0:
        return "—"
    # Exporté en min × 10^9 + max
    lo, hi = divmod(int(v), 10**9)
    return _fmt_money(hi) if lo in (0, hi) else f"{_fmt_money(lo)}-{_fmt_money(hi)}"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme et convertit le CSV brut."""
    df = df.copy()
    df.rename(columns=CSV_RENAME, inplace=True)
    df.drop(columns=[c for c in CSV_DROP if c in df.columns], inplace=True)

    for km_col in ("Distance", "Dist/90"):
        if km_col in df.columns:
            df[km_col] = (
                df[km_col].astype(str).str.replace("km", "", regex=False).str.strip()
            )

    for col in df.columns:
        if col not in NON_NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Apps exporté en champ de bits : titularisations << 16 | entrées en jeu
    if "Apps" in df.columns:
        df["Apps"] = df["Apps"] // 65536 + df["Apps"] % 65536
    if "OP-KP/90" in df.columns and "OP-KP" not in df.columns:
        df["OP-KP"] = df["OP-KP/90"] * df.get("Mins", 0) / 90
    if "xSv %" in df.columns:
        df["xSv %"] = df["xSv %"] / 100
    return df


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute postes, score défensif et colonnes calculées."""
    df = df.copy()
    if "Transfer Value" in df.columns:
        df["Transfer Value"] = df["Transfer Value"].apply(_fmt_transfer_value)
    if "Position" in df.columns:
        df["_pos_combos"] = df["Position"].apply(parse_position)

    df[SCORE_COL] = df.apply(defensive_actions_90, axis=1)
    return add_calculated_cols(df)


def merge_exports(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Concatène des exports nettoyés et fusionne les lignes de même UID.

    Totaux additionnés, autres stats moyennées pondérées par les minutes,
    ratios FM recalculés, attributs (club, âge, valeur…) repris du dernier
    export qui les renseigne.
    """
    df = pd.concat(frames, ignore_index=True, sort=False)
    stats = [
        c
        for c in df.select_dtypes("number").columns
        if c not in NON_NUMERIC_COLS and c not in NUMERIC_ATTRIBUTE_COLS
    ]
    if "UID" in df.columns and df["UID"].duplicated().any():
        dup = df["UID"].duplicated(keep=False)
        rows = df[dup]
        uid = rows["UID"]
        groups = rows.groupby(uid, sort=False)
        merged = groups.last()

        totals = [c for c in stats if c in TOTAL_COLS]
        if totals:
            merged[totals] = groups[totals].sum()

        rates = [c for c in stats if c not in TOTAL_COLS]
        if rates:
            mins = (
                rows["Mins"].fillna(0)
                if "Mins" in rows.columns
                else pd.Series(1.0, index=rows.index)
            )
            # Une valeur absente d'un export ne pèse pas dans la moyenne
            vals = rows[rates]
            weights = vals.notna().mul(mins, axis=0).groupby(uid, sort=False).sum()
            weighted = vals.mul(mins, axis=0).groupby(uid, sort=False).sum()
            merged[rates] = (weighted / weights.replace(0, np.nan)).fillna(
                groups[rates].mean()
            )

        for col, (num, den, scale) in RATIO_COLS.items():
            if {col, num, den} <= set(merged.columns):
                merged[col] = (
                    merged[num] * scale / merged[den].replace(0, np.nan)
                ).fillna(0)

        merged = merged.drop(columns="UID", errors="ignore").reset_index()
        df = pd.concat([df[~dup], merged[df.columns]], ignore_index=True)

    # Colonnes absentes de l'un des exports
    df[stats] = df[stats].fillna(0)
    return df


def build_dataset(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Fusionne un ou plusieurs exports nettoyés puis les enrichit."""
    return _enrich(merge_exports(frames))


def _read_csv(src) -> pd.DataFrame:
    try:
        return pd.read_csv(src, encoding="utf-8-sig", **_READ_OPTS)
    except UnicodeDecodeError:
        if hasattr(src, "seek"):
            src.seek(0)
        return pd.read_csv(src, encoding="latin-1", **_READ_OPTS)


@st.cache_data
def load_from_path(path: str) -> pd.DataFrame:
    """Export nettoyé, à passer à build_dataset."""
    return _clean(_read_csv(path))


def load_from_upload(f) -> pd.DataFrame:
    """Export importé nettoyé, à passer à build_dataset."""
    return _clean(_read_csv(f))
