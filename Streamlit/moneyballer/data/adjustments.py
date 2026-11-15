"""Ajustement des stats par club : modificateur de ligue et possession."""

import pandas as pd

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
        "Hdr %",
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
        for cols, factor in ((OFF_COLS, f_off), (DEF_COLS, f_def), (NEU_COLS, f_neu)):
            if abs(factor - 1.0) < 1e-6:
                continue
            for col in cols:
                if col in df.columns:
                    df.loc[mask, col] = df.loc[mask, col] * factor
    return df
