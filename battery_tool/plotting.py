from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go

from .geometry import compute_pack_bounds_mm, generate_cell_centers_mm
from .models import CellSpec, PackConfig


def pack_3d_figure(cell: CellSpec, cfg: PackConfig, highlight_n: int | None = None) -> go.Figure:
    """
    Creates a lightweight 3D view (cell centers + pack bounding box).

    Notes:
      Plotly marker size is in pixels, so this is a visual schematic, not CAD-accurate.
    """
    centers = generate_cell_centers_mm(cell, cfg)
    bounds = compute_pack_bounds_mm(cell, cfg)

    n = centers.shape[0]
    cell_used = cfg.cell_count
    if highlight_n is None:
        highlight_n = min(cell_used, n)
    highlight_n = max(0, min(int(highlight_n), n))

    used_mask = np.zeros(n, dtype=bool)
    used_mask[:highlight_n] = True

    fig = go.Figure()

    fig.add_trace(
        go.Scatter3d(
            x=centers[~used_mask, 0],
            y=centers[~used_mask, 1],
            z=centers[~used_mask, 2],
            mode="markers",
            name="Empty slots",
            marker={"size": 4, "color": "rgba(120,120,120,0.35)"},
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=centers[used_mask, 0],
            y=centers[used_mask, 1],
            z=centers[used_mask, 2],
            mode="markers",
            name="Cells (counted)",
            marker={"size": 5, "color": "#1f77b4"},
            text=[f"cell #{i+1}" for i in range(highlight_n)],
            hovertemplate="%{text}<br>x=%{x:.1f}mm y=%{y:.1f}mm z=%{z:.1f}mm<extra></extra>",
        )
    )

    # Bounding box (wireframe)
    x0, x1 = bounds.x_min, bounds.x_max
    y0, y1 = bounds.y_min, bounds.y_max
    z0, z1 = bounds.z_min, bounds.z_max
    lines = np.array(
        [
            # bottom rectangle
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z0],
            # vertical up
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
            [x0, y0, z1],
            # connect top to bottom corners
            [x1, y0, z1],
            [x1, y0, z0],
            [x1, y1, z0],
            [x1, y1, z1],
            [x0, y1, z1],
            [x0, y1, z0],
        ],
        dtype=float,
    )

    fig.add_trace(
        go.Scatter3d(
            x=lines[:, 0],
            y=lines[:, 1],
            z=lines[:, 2],
            mode="lines",
            name="Pack bounds",
            line={"width": 3, "color": "rgba(0,0,0,0.35)"},
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h"),
        title="Battery pack layout (schematic 3D)",
    )
    return fig


def config_to_json(cell: CellSpec, cfg: PackConfig) -> str:
    payload = {"cell": cell.__dict__, "pack": cfg.__dict__}
    return json.dumps(payload, indent=2, sort_keys=True)

