"""A tile-grid map of Brazilian states (one square per state, laid out roughly like the country).

Used instead of a geographic map so it needs no external map files and works offline.
The layout is static reference data, not business logic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# state -> (column, row); row 0 is the north. All 27 units, each position unique.
GRID: dict[str, tuple[int, int]] = {
    "RR": (2, 0), "AP": (4, 0),
    "AM": (1, 1), "PA": (3, 1), "MA": (4, 1), "CE": (5, 1), "RN": (6, 1),
    "AC": (0, 2), "RO": (1, 2), "MT": (2, 2), "TO": (3, 2), "PI": (4, 2),
    "PE": (5, 2), "PB": (6, 2),
    "MS": (2, 3), "GO": (3, 3), "DF": (4, 3), "BA": (5, 3), "AL": (6, 3),
    "SP": (3, 4), "MG": (4, 4), "ES": (5, 4), "SE": (6, 4),
    "PR": (3, 5), "RJ": (4, 5),
    "SC": (3, 6),
    "RS": (3, 7),
}  # fmt: skip


def tile_map(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    value_format: str = "{:,.1f}",
    colorscale: str = "Blues",
    hover_cols: dict[str, str] | None = None,
) -> go.Figure:
    """One tile per state coloured by ``value_col``; ``hover_cols`` maps column -> hover label."""
    n_cols = max(c for c, _ in GRID.values()) + 1
    n_rows = max(r for _, r in GRID.values()) + 1
    z = np.full((n_rows, n_cols), np.nan)
    label = np.full((n_rows, n_cols), "", dtype=object)
    hover = np.full((n_rows, n_cols), "", dtype=object)

    for state, (col, row) in GRID.items():
        match = df[df["state"] == state]
        if match.empty:
            continue
        record = match.iloc[0]
        value = record[value_col]
        if pd.isna(value):
            continue
        z[row, col] = float(value)
        label[row, col] = f"{state}<br>{value_format.format(float(value))}"
        lines = [f"<b>{state}</b>", f"{title}: {value_format.format(float(value))}"]
        for column, text in (hover_cols or {}).items():
            cell = record[column]
            lines.append(f"{text}: {cell:,.1f}" if isinstance(cell, float) else f"{text}: {cell:,}")
        hover[row, col] = "<br>".join(lines)

    fig = go.Figure(
        go.Heatmap(
            z=z,
            text=label,
            texttemplate="%{text}",
            hovertext=hover,
            hoverinfo="text",
            xgap=4,
            ygap=4,
            colorscale=colorscale,
            colorbar={"title": title},
        )
    )
    fig.update_yaxes(autorange="reversed", showticklabels=False, showgrid=False, zeroline=False)
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(height=460, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return fig
