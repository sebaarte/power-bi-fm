"""Nuage de points Plotly interactif."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from moneyballer.config import PLAYER_COLORS

_HOVER_DETAILS = (
    "Note: %{customdata[0]:.2f}<br>"
    "Mins: %{customdata[1]:.0f}<br>"
    "Apps: %{customdata[2]}<br>"
    "Valeur transfert: %{customdata[3]}<br>"
    "Position: %{customdata[4]}<br>"
    "Âge: %{customdata[5]:.0f}<extra></extra>"
)


def _hover_data(df: pd.DataFrame) -> np.ndarray:
    n = len(df)

    def num(col):
        return df[col].fillna(0.0).values if col in df.columns else np.zeros(n)

    def txt(col):
        return (
            df[col].fillna("—").astype(str).values
            if col in df.columns
            else np.full(n, "—")
        )

    return np.column_stack(
        [
            num("Av Rat"),
            num("Mins"),
            txt("Apps"),
            txt("Transfer Value"),
            txt("Position"),
            num("Age"),
        ]
    )


def _player_hover(rows: pd.DataFrame) -> list:
    def mean(col):
        return float(rows[col].mean()) if col in rows.columns else 0.0

    def first(col):
        return str(rows[col].iloc[0]) if col in rows.columns else "—"

    return [
        mean("Av Rat"),
        mean("Mins"),
        first("Apps"),
        first("Transfer Value"),
        first("Position"),
        mean("Age"),
    ]


def _iqr_outlier(v: np.ndarray, k: float) -> np.ndarray:
    finite = v[np.isfinite(v)]
    q1, q3 = np.percentile(finite, [25, 75])
    iqr = q3 - q1
    return (v < q1 - k * iqr) | (v > q3 + k * iqr)


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
    customdata = _hover_data(pop)
    mask = np.isfinite(x_data) & np.isfinite(y_data)

    # Détection outliers (IQR bivarié)
    if show_outliers and mask.sum() >= 4:
        outlier_mask = mask & (
            _iqr_outlier(x_data, outlier_k) | _iqr_outlier(y_data, outlier_k)
        )
        normal_mask = mask & ~outlier_mask
    else:
        outlier_mask = np.zeros(len(mask), dtype=bool)
        normal_mask = mask

    hover_tmpl = (
        "<b>%{text}</b><br>"
        + x_label
        + ": %{x:.2f}<br>"
        + y_label
        + ": %{y:.2f}<br>"
        + _HOVER_DETAILS
    )

    fig = go.Figure()
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

    # Tendance (exclut les outliers pour une régression robuste)
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
        fig.add_trace(
            go.Scatter(
                x=[px],
                y=[py],
                mode="markers+text",
                marker=dict(color=c, size=12, line=dict(color="white", width=1.5)),
                text=[p["name"]],
                customdata=[_player_hover(rows)],
                textposition="top right",
                textfont=dict(color=c, size=10),
                name=p["name"],
                hovertemplate=hover_tmpl,
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
