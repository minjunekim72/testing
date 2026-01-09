from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from .geometry import compute_pack_bounds_mm, generate_cell_centers_mm
from .models import CellSpec, PackConfig


@dataclass(frozen=True)
class EnclosureSpec:
    include: bool = True
    clearance_mm: float = 2.0  # clearance between outermost cells and inner wall
    wall_mm: float = 2.0  # enclosure wall thickness (exported as a solid outer block)


def _cell_mesh_at_origin(cell: CellSpec, sections: int = 32) -> trimesh.Trimesh:
    """
    Returns a single cell mesh centered at origin.

    Conventions:
      - XY is the pack plane
      - Z is "height"
      - Mesh is centered at (0,0,0)
    """
    cell.validate()
    sections = int(max(8, sections))

    if cell.form_factor == "cylindrical":
        radius = float(cell.diameter_mm) / 2.0
        height = float(cell.height_mm)
        m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
        # trimesh cylinders are centered on origin already (Z spans [-h/2, h/2])
        return m

    # prismatic
    w = float(cell.width_mm)
    l = float(cell.length_mm)
    h = float(cell.height_mm)
    m = trimesh.creation.box(extents=(w, l, h))
    return m


def build_pack_scene_mm(
    cell: CellSpec,
    cfg: PackConfig,
    *,
    cell_count: int | None = None,
    sections: int = 32,
    enclosure: EnclosureSpec | None = None,
) -> trimesh.Scene:
    """
    Build a CAD-like 3D scene (cells + optional enclosure).

    Units:
      - All geometry is in millimeters.
    """
    cell.validate()
    cfg.validate()

    if cell_count is None:
        cell_count = cfg.cell_count
    cell_count = int(max(0, min(cell_count, cfg.capacity_slots)))

    if enclosure is None:
        enclosure = EnclosureSpec()

    centers = generate_cell_centers_mm(cell, cfg)[:cell_count]
    scene = trimesh.Scene()

    base = _cell_mesh_at_origin(cell, sections=sections)
    for i in range(cell_count):
        m = base.copy()
        m.apply_translation(centers[i])
        # Store as separate geometry for easier CAD import/selection
        scene.add_geometry(m, geom_name=f"cell_{i+1:05d}")

    if enclosure.include and cell_count > 0:
        b = compute_pack_bounds_mm(cell, cfg)
        # Use the full layout bounds (not just used cells) so the enclosure matches the shown grid.
        # Then expand with clearance + wall thickness.
        clearance = max(0.0, float(enclosure.clearance_mm))
        wall = max(0.0, float(enclosure.wall_mm))

        inner_x = (b.x_max - b.x_min) + 2.0 * clearance
        inner_y = (b.y_max - b.y_min) + 2.0 * clearance
        inner_z = (b.z_max - b.z_min) + 2.0 * clearance

        outer_x = inner_x + 2.0 * wall
        outer_y = inner_y + 2.0 * wall
        outer_z = inner_z + 2.0 * wall

        enclosure_mesh = trimesh.creation.box(extents=(outer_x, outer_y, outer_z))
        # center enclosure on same origin as cells
        scene.add_geometry(enclosure_mesh, geom_name="enclosure_outer")

    return scene


def export_scene_stl_bytes(scene: trimesh.Scene) -> bytes:
    # Scene -> single mesh for STL export
    mesh = trimesh.util.concatenate([g for g in scene.geometry.values()]) if scene.geometry else trimesh.Trimesh()
    return trimesh.exchange.stl.export_stl(mesh)


def export_scene_obj_bytes(scene: trimesh.Scene) -> bytes:
    # trimesh returns string for OBJ; encode to bytes
    s = trimesh.exchange.obj.export_obj(scene)
    return s.encode("utf-8")


def scene_to_mesh(scene: trimesh.Scene) -> trimesh.Trimesh:
    """Concatenate scene into a single mesh (useful for Plotly Mesh3d)."""
    if not scene.geometry:
        return trimesh.Trimesh()
    return trimesh.util.concatenate([g for g in scene.geometry.values()])

