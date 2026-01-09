from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .geometry import CylindricalGeometry, PouchPrismaticGeometry
from .units import mm_to_cm


def draw_3d_cylindrical(geom: CylindricalGeometry) -> go.Figure:
    geom.validate()
    r = mm_to_cm(geom.outer_diameter_mm) / 2.0
    h = mm_to_cm(geom.height_mm)

    theta = np.linspace(0, 2 * np.pi, 50)
    z = np.linspace(0, h, 2)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x = r * np.cos(theta_grid)
    y = r * np.sin(theta_grid)

    fig = go.Figure(
        data=[
            go.Surface(x=x, y=y, z=z_grid, showscale=False, opacity=0.85),
        ]
    )
    fig.update_layout(
        title="3D view (cylindrical)",
        scene=dict(aspectmode="data", xaxis_title="cm", yaxis_title="cm", zaxis_title="cm"),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def draw_3d_pouch(geom: PouchPrismaticGeometry) -> go.Figure:
    geom.validate()
    w = mm_to_cm(geom.width_mm)
    h = mm_to_cm(geom.height_mm)
    t = mm_to_cm(geom.thickness_mm)

    # Build a rectangular prism as a Mesh3d
    verts = np.array(
        [
            [0, 0, 0],
            [w, 0, 0],
            [w, h, 0],
            [0, h, 0],
            [0, 0, t],
            [w, 0, t],
            [w, h, t],
            [0, h, t],
        ],
        dtype=float,
    )
    i = [0, 0, 0, 1, 1, 2, 4, 4, 5, 6, 3, 7]
    j = [1, 2, 3, 2, 5, 3, 5, 7, 6, 7, 7, 6]
    k = [2, 3, 1, 5, 6, 6, 6, 6, 7, 4, 4, 2]

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                i=i,
                j=j,
                k=k,
                opacity=0.85,
            )
        ]
    )
    fig.update_layout(
        title="3D view (pouch/prismatic)",
        scene=dict(aspectmode="data", xaxis_title="cm", yaxis_title="cm", zaxis_title="cm"),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig

