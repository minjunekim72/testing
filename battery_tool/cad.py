from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from .geometry import compute_pack_bounds_mm, generate_cell_centers_mm
from .models import CellSpec, PackConfig


@dataclass(frozen=True)
class EnclosureSpec:
    include: bool = True
    style: str = "box"  # "box" | "battery_case"
    clearance_mm: float = 2.0  # clearance between outermost cells and inner wall
    wall_mm: float = 2.0  # enclosure wall thickness (exported as a solid outer block)

    # Battery-case styling (simple, boolean-free "union" details)
    head_height_mm: float = 14.0  # extra top cap height
    head_inset_mm: float = 4.0  # how much the top cap shrinks in X/Y
    base_lip_mm: float = 3.0  # bottom plate thickness
    base_overhang_mm: float = 3.0  # bottom plate X/Y overhang

    terminal_diameter_mm: float = 10.0
    terminal_height_mm: float = 10.0
    terminal_inset_mm: float = 10.0  # inset from outer edges
    terminal_spacing_y_mm: float = 0.0  # optional shift along Y (0 keeps symmetric)

    rib_count: int = 5
    rib_depth_mm: float = 1.5
    rib_width_mm: float = 3.0


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


def _add_battery_case_geometry_mm(
    scene: trimesh.Scene,
    *,
    outer_x: float,
    outer_y: float,
    outer_z: float,
    spec: EnclosureSpec,
    sections: int,
) -> None:
    """
    Adds a simple battery-case style enclosure and terminals.

    This is intentionally "CAD-friendly" (solid primitives) and avoids booleans.
    """
    # Main body box (centered)
    body = trimesh.creation.box(extents=(outer_x, outer_y, outer_z))
    scene.add_geometry(body, geom_name="enclosure_body")

    # Bottom lip / base plate (slightly larger in X/Y)
    lip_t = max(0.1, float(spec.base_lip_mm))
    over = max(0.0, float(spec.base_overhang_mm))
    base = trimesh.creation.box(extents=(outer_x + 2.0 * over, outer_y + 2.0 * over, lip_t))
    base.apply_translation((0.0, 0.0, -(outer_z / 2.0) - (lip_t / 2.0)))
    scene.add_geometry(base, geom_name="enclosure_base")

    # Top head/cap (slightly inset, sits on top)
    head_h = max(0.1, float(spec.head_height_mm))
    inset = max(0.0, float(spec.head_inset_mm))
    head_x = max(1.0, outer_x - 2.0 * inset)
    head_y = max(1.0, outer_y - 2.0 * inset)
    head = trimesh.creation.box(extents=(head_x, head_y, head_h))
    head.apply_translation((0.0, 0.0, (outer_z / 2.0) + (head_h / 2.0)))
    scene.add_geometry(head, geom_name="enclosure_head")

    # Simple ribs on two side faces (like molded stiffeners)
    rib_n = int(max(0, spec.rib_count))
    if rib_n > 0:
        rib_depth = max(0.1, float(spec.rib_depth_mm))
        rib_w = max(0.5, float(spec.rib_width_mm))
        # distribute along Y
        ys = np.linspace(-outer_y / 2.0 + rib_w, outer_y / 2.0 - rib_w, rib_n)
        for idx, y in enumerate(ys, start=1):
            rib = trimesh.creation.box(extents=(rib_depth, rib_w, outer_z * 0.75))
            rib.apply_translation((outer_x / 2.0 + rib_depth / 2.0, float(y), 0.0))
            scene.add_geometry(rib, geom_name=f"enclosure_rib_r_{idx:02d}")

            rib2 = rib.copy()
            rib2.apply_translation((-outer_x - rib_depth, 0.0, 0.0))  # mirror to -X side
            scene.add_geometry(rib2, geom_name=f"enclosure_rib_l_{idx:02d}")

    # Terminals: two posts on the head (near +X corners)
    post_r = max(1.0, float(spec.terminal_diameter_mm) / 2.0)
    post_h = max(1.0, float(spec.terminal_height_mm))
    inset_t = max(0.0, float(spec.terminal_inset_mm))
    y_shift = float(spec.terminal_spacing_y_mm)

    # positions (roughly like the reference image: both on the top, separated in X)
    z_top = (outer_z / 2.0) + head_h + (post_h / 2.0)
    x_pos = (outer_x / 2.0) - inset_t - post_r
    x_neg = -(outer_x / 2.0) + inset_t + post_r
    y_pos = (outer_y / 2.0) - inset_t - post_r + y_shift
    y_neg = y_pos  # keep same Y alignment for a classic top layout

    post = trimesh.creation.cylinder(radius=post_r, height=post_h, sections=max(12, sections))
    pos_post = post.copy()
    pos_post.apply_translation((x_pos, y_pos, z_top))
    scene.add_geometry(pos_post, geom_name="terminal_pos")

    neg_post = post.copy()
    neg_post.apply_translation((x_neg, y_neg, z_top))
    scene.add_geometry(neg_post, geom_name="terminal_neg")

    # Simple raised symbols on head: "+" near pos, "-" near neg (thin boxes)
    sym_t = max(0.4, min(1.5, head_h * 0.15))
    sym_z = (outer_z / 2.0) + head_h + (sym_t / 2.0)
    sym_size = post_r * 1.4
    bar_w = max(0.8, sym_size * 0.22)

    # Plus: two bars
    plus_a = trimesh.creation.box(extents=(sym_size, bar_w, sym_t))
    plus_b = trimesh.creation.box(extents=(bar_w, sym_size, sym_t))
    plus_a.apply_translation((x_pos, y_pos, sym_z))
    plus_b.apply_translation((x_pos, y_pos, sym_z))
    scene.add_geometry(plus_a, geom_name="mark_plus_a")
    scene.add_geometry(plus_b, geom_name="mark_plus_b")

    # Minus: one bar
    minus = trimesh.creation.box(extents=(sym_size, bar_w, sym_t))
    minus.apply_translation((x_neg, y_neg, sym_z))
    scene.add_geometry(minus, geom_name="mark_minus")


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

        if enclosure.style == "battery_case":
            _add_battery_case_geometry_mm(
                scene,
                outer_x=float(outer_x),
                outer_y=float(outer_y),
                outer_z=float(outer_z),
                spec=enclosure,
                sections=int(sections),
            )
        else:
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

