"""Radar matplotlib."""

import matplotlib.pyplot as plt
import numpy as np

from moneyballer.config import BEST_COLOR, MEAN_COLOR, P95_COLOR, PLAYER_COLORS


def radar_labels(cols: list[str]) -> list[str]:
    return [c.replace("/90", "\n/90") if len(c) > 9 else c for c in cols]


def draw_radar(
    refs: dict,
    best_name: str,
    players: list,
    cols: list,
    labels: list,
    *,
    figsize: tuple[float, float] = (7, 7),
    show_legend: bool = True,
) -> plt.Figure:
    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]

    def close(a):
        return np.append(a, a[0])

    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))
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

    ax.plot(angles, close(mean_v), color=MEAN_COLOR, lw=1.5, ls="--", label="Moyenne")
    ax.fill(angles, close(mean_v), color=MEAN_COLOR, alpha=0.08)
    ax.plot(angles, close(p95_v), color=P95_COLOR, lw=1.5, ls="--", label="P95")
    ax.fill(angles, close(p95_v), color=P95_COLOR, alpha=0.08)
    ax.plot(
        angles, close(best_v), color=BEST_COLOR, lw=2, label=f"Meilleur — {best_name}"
    )
    ax.fill(angles, close(best_v), color=BEST_COLOR, alpha=0.12)

    for i, p in enumerate(players):
        c = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        ax.plot(angles, close(p["values"]), color=c, lw=2.5, label=p["name"])
        ax.fill(angles, close(p["values"]), color=c, alpha=0.15)
        ax.scatter(angles[:-1], p["values"], color=c, s=30, zorder=5)

    if show_legend:
        ax.legend(
            loc="upper right",
            bbox_to_anchor=(1.45, 1.15),
            facecolor="#16161e",
            edgecolor="#2a2a3a",
            labelcolor="#e0e0e0",
            fontsize=8.5,
            framealpha=0.95,
        )
    fig.tight_layout()
    return fig
