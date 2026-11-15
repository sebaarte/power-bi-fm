"""Métriques dérivées : score défensif, colonnes calculées, formules personnalisées."""

import numpy as np
import pandas as pd


def defensive_actions_90(row: pd.Series) -> float:
    """Formule DAX exacte.

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


def add_calculated_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Colonnes calculées portées depuis Power Query."""

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
        df["Non pen xG Overperformance"] * 90, _c("Mins")
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
    df["xGC/90"] = _safe(df["xGC"] * 90, _c("Mins"))
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
    df["Tackles Failed/90"] = _safe(df["Tackles Failed"] * 90, _c("Mins"))
    df["Key Tackles %"] = _safe(_c("K Tck"), _c("Tck W"))
    df["Tackle Quality"] = _safe(_c("Tck W"), _c("Fls"))
    df["Hdr %"] = _safe(_c("Hdrs"), _c("Hdrs A"))
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
    df["Clean Sheet Ratio"] = _safe(_c("Clean Sheets"), _c("Apps"))

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


def apply_formulas(pop: pd.DataFrame, formulas: list[dict]) -> pd.DataFrame:
    """Ajoute une colonne par formule : moyenne des percentiles de ses composantes."""
    for formula in formulas:
        comp_cols = [c["col"] for c in formula["components"] if c["col"] in pop.columns]
        if comp_cols:
            pop[formula["name"]] = pd.concat(
                [pop[c].rank(pct=True) for c in comp_cols], axis=1
            ).mean(axis=1)
        else:
            pop[formula["name"]] = 0.0
    return pop
