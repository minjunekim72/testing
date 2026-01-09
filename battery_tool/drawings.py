from __future__ import annotations

from dataclasses import dataclass

import io

import ezdxf

from .geometry import compute_pack_bounds_mm, generate_cell_centers_mm
from .models import CellSpec, PackConfig


@dataclass(frozen=True)
class DrawingSpec:
    include_enclosure_outline: bool = True
    enclosure_clearance_mm: float = 2.0
    enclosure_wall_mm: float = 2.0


def _enclosure_outer_bounds_xy_mm(cell: CellSpec, cfg: PackConfig, spec: DrawingSpec) -> tuple[float, float, float, float]:
    b = compute_pack_bounds_mm(cell, cfg)
    clearance = max(0.0, float(spec.enclosure_clearance_mm))
    wall = max(0.0, float(spec.enclosure_wall_mm))

    x0 = b.x_min - clearance - wall
    x1 = b.x_max + clearance + wall
    y0 = b.y_min - clearance - wall
    y1 = b.y_max + clearance + wall
    return x0, x1, y0, y1


def export_top_view_svg(
    cell: CellSpec,
    cfg: PackConfig,
    *,
    cell_count: int | None = None,
    spec: DrawingSpec | None = None,
) -> str:
    """
    Export a very simple top-view SVG (XY plane).
    Units are in mm.
    """
    cell.validate()
    cfg.validate()
    if spec is None:
        spec = DrawingSpec()
    if cell_count is None:
        cell_count = cfg.cell_count
    cell_count = int(max(0, min(cell_count, cfg.capacity_slots)))

    centers = generate_cell_centers_mm(cell, cfg)[:cell_count]

    # ViewBox bounds
    b = compute_pack_bounds_mm(cell, cfg)
    pad = 5.0
    x0, x1 = b.x_min - pad, b.x_max + pad
    y0, y1 = b.y_min - pad, b.y_max + pad

    if spec.include_enclosure_outline:
        ex0, ex1, ey0, ey1 = _enclosure_outer_bounds_xy_mm(cell, cfg, spec)
        x0, x1 = min(x0, ex0 - pad), max(x1, ex1 + pad)
        y0, y1 = min(y0, ey0 - pad), max(y1, ey1 + pad)

    width = x1 - x0
    height = y1 - y0

    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.3f} {-(y1):.3f} {width:.3f} {height:.3f}" '
        f'width="{width:.3f}mm" height="{height:.3f}mm">'
    )
    # Flip Y for typical CAD-ish top view (so up is +Y visually)
    parts.append(f'<g transform="scale(1,-1) translate(0,{-(y0+y1):.6f})">')

    if spec.include_enclosure_outline:
        ex0, ex1, ey0, ey1 = _enclosure_outer_bounds_xy_mm(cell, cfg, spec)
        parts.append(
            f'<rect x="{ex0:.3f}" y="{ey0:.3f}" width="{(ex1-ex0):.3f}" height="{(ey1-ey0):.3f}" '
            'fill="none" stroke="#000" stroke-width="0.5"/>'
        )

    if cell.form_factor == "cylindrical":
        r = float(cell.diameter_mm) / 2.0
        for (x, y, _z) in centers:
            parts.append(
                f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" fill="none" stroke="#1f77b4" stroke-width="0.4"/>'
            )
    else:
        w = float(cell.width_mm)
        l = float(cell.length_mm)
        for (x, y, _z) in centers:
            parts.append(
                f'<rect x="{(x-w/2):.3f}" y="{(y-l/2):.3f}" width="{w:.3f}" height="{l:.3f}" '
                'fill="none" stroke="#1f77b4" stroke-width="0.4"/>'
            )

    parts.append("</g></svg>")
    return "\n".join(parts)


def export_top_view_dxf_bytes(
    cell: CellSpec,
    cfg: PackConfig,
    *,
    cell_count: int | None = None,
    spec: DrawingSpec | None = None,
) -> bytes:
    """
    Export a basic top-view DXF (circles/rectangles + optional enclosure outline).
    Units are mm.
    """
    cell.validate()
    cfg.validate()
    if spec is None:
        spec = DrawingSpec()
    if cell_count is None:
        cell_count = cfg.cell_count
    cell_count = int(max(0, min(cell_count, cfg.capacity_slots)))

    centers = generate_cell_centers_mm(cell, cfg)[:cell_count]

    doc = ezdxf.new(setup=True)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()

    if spec.include_enclosure_outline and cell_count > 0:
        ex0, ex1, ey0, ey1 = _enclosure_outer_bounds_xy_mm(cell, cfg, spec)
        msp.add_lwpolyline([(ex0, ey0), (ex1, ey0), (ex1, ey1), (ex0, ey1), (ex0, ey0)], close=True, dxfattribs={"layer": "ENCLOSURE"})

    if cell.form_factor == "cylindrical":
        r = float(cell.diameter_mm) / 2.0
        for (x, y, _z) in centers:
            msp.add_circle((float(x), float(y)), r, dxfattribs={"layer": "CELLS"})
    else:
        w = float(cell.width_mm)
        l = float(cell.length_mm)
        for (x, y, _z) in centers:
            x0 = float(x) - w / 2.0
            x1 = float(x) + w / 2.0
            y0 = float(y) - l / 2.0
            y1 = float(y) + l / 2.0
            msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], close=True, dxfattribs={"layer": "CELLS"})

    # ezdxf writes text DXF; export to string then encode.
    sio = io.StringIO()
    doc.write(sio)
    return sio.getvalue().encode("utf-8")

