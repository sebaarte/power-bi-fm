"""Persistance JSON des réglages utilisateur (ajustements, formules)."""

import json
from pathlib import Path

import pandas as pd

from moneyballer.config import ADJ_SETTINGS_FILE, CUSTOM_COLS_FILE


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: Path, data) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_adj_settings() -> tuple[dict, dict]:
    """Retourne (club_settings, ligue_mod).

    club_settings : {club: {Club, Ligue, Possession}}
    ligue_mod     : {ligue: modificateur}
    """
    data = _read_json(ADJ_SETTINGS_FILE)
    if data is None:
        return {}, {}
    try:
        # Ancien format : liste plate Club/Possession/Modificateur
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
        return {}, {}


def save_adj_settings(adj_df: pd.DataFrame, ligue_mod: dict) -> None:
    """Sauvegarde la possession par club et le modificateur par ligue."""
    _write_json(
        ADJ_SETTINGS_FILE,
        {
            "possessions": adj_df[["Club", "Ligue", "Possession"]].to_dict(
                orient="records"
            ),
            "modificateurs": [
                {"Ligue": lg, "Modificateur": mod} for lg, mod in ligue_mod.items()
            ],
        },
    )


def load_custom_cols() -> list[dict]:
    """Retourne les formules personnalisées : [{name, components: [{col, weight}]}]."""
    data = _read_json(CUSTOM_COLS_FILE)
    return data if isinstance(data, list) else []


def save_custom_cols(cols: list[dict]) -> None:
    _write_json(CUSTOM_COLS_FILE, cols)
