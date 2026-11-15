"""Chemins et constantes partagés par toute l'application."""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = APP_DIR.parent / "output_files"
ADJ_SETTINGS_FILE = APP_DIR / "adj_settings.json"
CUSTOM_COLS_FILE = APP_DIR / "custom_cols.json"

# Colonnes requises par la vue Data
STATS_COLS = [
    "Clr/90",
    "Int/90",
    "Shts Blckd/90",
    "Pres C/90",
    "Tck/90",
    "K Tck/90",
    "Hdrs W/90",
]
SCORE_COL = "Defensive Actions/90"

# Colonnes numériques techniques, jamais proposées comme statistiques
INTERNAL_COLS = frozenset({"UID", "_pos_combos"})

MAX_PLAYERS = 5
PLAYER_COLORS = ["#ff4d4d", "#a259ff", "#00e676", "#ff9800", "#00e5ff"]
MEAN_COLOR = "#FFFFFF"
P95_COLOR = "#f0a500"
BEST_COLOR = "#00bfff"
