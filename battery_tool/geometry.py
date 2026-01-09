from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import CellSpec, PackConfig


@dataclass(frozen=True)
class PackBoundsMM:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float


def _cell_pitch_mm(cell: CellSpec, cfg: PackConfig) -> tuple[float, float, float]:
    """Returns center-to-center pitch along x, y, z."""
    if cell.form_factor == "cylindrical":
        d = float(cell.diameter_mm)
        h = float(cell.height_mm)
        pitch_xy = d + cfg.spacing_mm
        pitch_z = h + cfg.spacing_mm
        return pitch_xy, pitch_xy, pitch_z

    # prismatic: use width/length for x/y pitch
    w = float(cell.width_mm)
    l = float(cell.length_mm)
    h = float(cell.height_mm)
    return w + cfg.spacing_mm, l + cfg.spacing_mm, h + cfg.spacing_mm


def generate_cell_centers_mm(cell: CellSpec, cfg: PackConfig) -> np.ndarray:
    """
    Generate 3D centers for a rectangular grid of cells.

    Returns:
      ndarray shape (N, 3) where N = rows*cols*layers.
    """
    cell.validate()
    cfg.validate()

    pitch_x, pitch_y, pitch_z = _cell_pitch_mm(cell, cfg)

    xs = np.arange(cfg.cols, dtype=float) * pitch_x
    ys = np.arange(cfg.rows, dtype=float) * pitch_y
    zs = np.arange(cfg.layers, dtype=float) * pitch_z

    centers = []
    for k, z in enumerate(zs):
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                centers.append((x, y, z))

    arr = np.array(centers, dtype=float)

    # Center around origin for nicer viewing
    arr[:, 0] -= (xs.max() if xs.size else 0) / 2.0
    arr[:, 1] -= (ys.max() if ys.size else 0) / 2.0
    arr[:, 2] -= (zs.max() if zs.size else 0) / 2.0
    return arr


def compute_pack_bounds_mm(cell: CellSpec, cfg: PackConfig) -> PackBoundsMM:
    """Compute a simple bounding box around the cell grid."""
    centers = generate_cell_centers_mm(cell, cfg)
    if centers.size == 0:
        return PackBoundsMM(0, 0, 0, 0, 0, 0)

    if cell.form_factor == "cylindrical":
        half_x = float(cell.diameter_mm) / 2.0
        half_y = float(cell.diameter_mm) / 2.0
        half_z = float(cell.height_mm) / 2.0
    else:
        half_x = float(cell.width_mm) / 2.0
        half_y = float(cell.length_mm) / 2.0
        half_z = float(cell.height_mm) / 2.0

    return PackBoundsMM(
        x_min=float(centers[:, 0].min() - half_x),
        x_max=float(centers[:, 0].max() + half_x),
        y_min=float(centers[:, 1].min() - half_y),
        y_max=float(centers[:, 1].max() + half_y),
        z_min=float(centers[:, 2].min() - half_z),
        z_max=float(centers[:, 2].max() + half_z),
    )

