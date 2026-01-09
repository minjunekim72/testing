from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go

from .cad import EnclosureSpec, build_pack_scene_mm, scene_to_mesh
from .geometry import compute_pack_bounds_mm, generate_cell_centers_mm
from .models import CellSpec, PackConfig


def _mesh3d_from_trimesh(mesh, *, color: str, name: str, opacity: float = 1.0) -> go.Mesh3d | None:
    if mesh is None or (not getattr(mesh, "vertices", None) is not None):
        return None
    if mesh.vertices is None or mesh.faces is None or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        return None
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    return go.Mesh3d(
        x=v[:, 0],
        y=v[:, 1],
        z=v[:, 2],
        i=f[:, 0],
        j=f[:, 1],
        k=f[:, 2],
        color=color,
        opacity=float(opacity),
        name=name,
        hoverinfo="skip",
    )


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


def pack_3d_cad_figure(
    cell: CellSpec,
    cfg: PackConfig,
    *,
    include_enclosure: bool = True,
    enclosure_style: str = "box",
    enclosure_clearance_mm: float = 2.0,
    enclosure_wall_mm: float = 2.0,
    mesh_sections: int = 28,
) -> go.Figure:
    """
    CAD-like 3D rendering (cells as solids + optional enclosure).

    Notes:
      - This is still a visualization; for CAD use the STL/OBJ export.
      - Resolution is controlled by mesh_sections (higher = smoother cylinders).
    """
    enclosure = EnclosureSpec(
        include=bool(include_enclosure),
        style=str(enclosure_style),
        clearance_mm=float(enclosure_clearance_mm),
        wall_mm=float(enclosure_wall_mm),
    )
    scene = build_pack_scene_mm(cell, cfg, sections=int(mesh_sections), enclosure=enclosure)

    fig = go.Figure()
    # Render parts with distinct colors for a more "product-like" look.
    if scene.geometry:
        # Cells (concatenate for performance)
        cell_meshes = [m for name, m in scene.geometry.items() if name.startswith("cell_")]
        try:
            import trimesh as _tm  # local import

            if cell_meshes:
                _s = _tm.Scene()
                for i, m in enumerate(cell_meshes):
                    _s.add_geometry(m, geom_name=f"c{i}")
                cells = scene_to_mesh(_s)
                t = _mesh3d_from_trimesh(
                    cells,
                    color="#1f77b4",
                    name="Cells",
                    opacity=0.95 if not include_enclosure else 0.65,
                )
                if t is not None:
                    fig.add_trace(t)
        except Exception:
            pass

        # Enclosure parts
        enc_meshes = [m for name, m in scene.geometry.items() if name.startswith("enclosure_")]
        if enc_meshes:
            try:
                import trimesh as _tm  # local import

                _s = _tm.Scene()
                for i, m in enumerate(enc_meshes):
                    _s.add_geometry(m, geom_name=f"e{i}")
                enc = scene_to_mesh(_s)
                t = _mesh3d_from_trimesh(enc, color="rgba(210,210,210,1.0)", name="Enclosure", opacity=0.55)
                if t is not None:
                    fig.add_trace(t)
            except Exception:
                pass

        # Terminals + markings (render separately for color)
        for name, m in scene.geometry.items():
            if name == "terminal_pos":
                t = _mesh3d_from_trimesh(m, color="#d62728", name="Positive terminal", opacity=1.0)
                if t is not None:
                    fig.add_trace(t)
            elif name == "terminal_neg":
                t = _mesh3d_from_trimesh(m, color="#1f77b4", name="Negative terminal", opacity=1.0)
                if t is not None:
                    fig.add_trace(t)
            elif name.startswith("mark_plus"):
                t = _mesh3d_from_trimesh(m, color="#d62728", name="+", opacity=1.0)
                if t is not None:
                    fig.add_trace(t)
            elif name == "mark_minus":
                t = _mesh3d_from_trimesh(m, color="#1f77b4", name="-", opacity=1.0)
                if t is not None:
                    fig.add_trace(t)

    # Add a wireframe bounds to aid orientation
    bounds = compute_pack_bounds_mm(cell, cfg)
    x0, x1 = bounds.x_min, bounds.x_max
    y0, y1 = bounds.y_min, bounds.y_max
    z0, z1 = bounds.z_min, bounds.z_max
    lines = np.array(
        [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
            [x0, y0, z1],
        ],
        dtype=float,
    )
    fig.add_trace(
        go.Scatter3d(
            x=lines[:, 0],
            y=lines[:, 1],
            z=lines[:, 2],
            mode="lines",
            name="Cell bounds",
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
        title="Battery (CAD-like solids)",
    )
    return fig


def config_to_json(cell: CellSpec, cfg: PackConfig) -> str:
    payload = {"cell": cell.__dict__, "pack": cfg.__dict__}
    return json.dumps(payload, indent=2, sort_keys=True)

