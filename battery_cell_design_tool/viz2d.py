from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from .geometry import CylindricalGeometry, PouchPrismaticGeometry


def draw_2d_cylindrical(geom: CylindricalGeometry):
    geom.validate()
    ro = geom.outer_radius_cm
    ri = geom.inner_radius_cm

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.add_patch(Circle((0, 0), ro, fill=False, linewidth=2))
    if ri > 0:
        ax.add_patch(Circle((0, 0), ri, fill=False, linewidth=1, linestyle="--"))

    ax.set_aspect("equal", adjustable="box")
    lim = ro * 1.15
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_title("2D cross-section (cylindrical)")
    ax.set_xlabel("cm")
    ax.set_ylabel("cm")
    ax.grid(True, alpha=0.25)

    ax.text(0, ro * 1.02, f"OD={geom.outer_diameter_mm:.1f} mm", ha="center", va="bottom")
    if ri > 0:
        ax.text(0, -ri * 1.1, f"Mandrel={geom.mandrel_diameter_mm:.1f} mm", ha="center", va="top")
    return fig


def draw_2d_pouch(geom: PouchPrismaticGeometry):
    geom.validate()
    w = geom.width_cm
    h = geom.height_cm
    m = geom.margin_cm

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, linewidth=2))
    ax.add_patch(Rectangle((m, m), w - 2 * m, h - 2 * m, fill=False, linewidth=1, linestyle="--"))
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("2D footprint (pouch/prismatic)")
    ax.set_xlabel("cm")
    ax.set_ylabel("cm")
    ax.grid(True, alpha=0.25)
    ax.text(w / 2, h + 0.1, f"W={geom.width_mm:.1f} mm, H={geom.height_mm:.1f} mm", ha="center", va="bottom")
    ax.text(w / 2, -0.15, f"T={geom.thickness_mm:.1f} mm", ha="center", va="top")
    ax.set_xlim(-0.2, w + 0.2)
    ax.set_ylim(-0.2, h + 0.4)
    return fig

