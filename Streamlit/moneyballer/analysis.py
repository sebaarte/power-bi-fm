"""Normalisation des statistiques et références (moyenne, P95, meilleur joueur)."""

import numpy as np
import pandas as pd

from moneyballer.config import INTERNAL_COLS, SCORE_COL


def stat_columns(df: pd.DataFrame) -> list[str]:
    """Colonnes numériques exploitables comme statistiques."""
    return [
        c for c in df.select_dtypes(include="number").columns if c not in INTERNAL_COLS
    ]


def percentile_of(pop: pd.DataFrame, col: str, value: float) -> float:
    """Part (0-100) de la population dont la valeur est ≤ value."""
    return float((pop[col] <= value).mean()) * 100


def compute_refs(
    pop: pd.DataFrame,
    cols: list,
    pct_mode: bool = False,
    score_col: str = SCORE_COL,
) -> tuple[dict, str]:
    """Retourne ({col: {min, max, mean, p95, best}}, nom du meilleur joueur selon score_col)."""
    refs = {}
    sc = score_col if score_col in pop.columns else SCORE_COL
    sc_series = pop[sc].dropna()
    # Score entièrement NaN : repli sur la première ligne
    best_idx = pop.index[0] if sc_series.empty else sc_series.idxmax()
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
    """Valeurs normalisées 0-1 d'un joueur sur chaque axe."""
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


def build_radar_players(
    players: list[dict],
    pop: pd.DataFrame,
    refs: dict,
    cols: list,
    pct_mode: bool,
    score_col: str,
) -> list[dict]:
    """Prépare les joueurs sélectionnés pour un radar : valeurs normalisées, brutes et score."""
    out = []
    for p in players:
        rows = pop[pop["Name"] == p["name"]]
        score = (
            float(rows[score_col].mean())
            if score_col in rows.columns and not rows.empty
            else p["score"]
        )
        out.append(
            {
                "name": p["name"],
                "values": player_values(p["row"], pop, refs, cols, pct_mode),
                "raw": {c: float(p["row"][c]) for c in cols if c in p["row"].index},
                "score": score,
            }
        )
    return out
