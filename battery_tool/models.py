from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CellSpec:
    """
    A very small cell model intended for early-stage pack sizing.

    Notes:
      - OCV is modeled as linear with SOC (simple, not chemistry-accurate).
      - Internal resistance is a single lumped value (no thermal / SOC effects).
    """

    name: str
    nominal_voltage_v: float
    capacity_ah: float
    internal_resistance_ohm: float
    max_continuous_a: float
    ocv_full_v: float
    ocv_empty_v: float
    cutoff_v: float

    # Geometry (used for 3D layout)
    form_factor: str = "cylindrical"  # "cylindrical" | "prismatic"
    diameter_mm: float | None = 18.0
    height_mm: float | None = 65.0
    width_mm: float | None = None
    length_mm: float | None = None

    def validate(self) -> None:
        if self.capacity_ah <= 0:
            raise ValueError("capacity_ah must be > 0")
        if self.nominal_voltage_v <= 0:
            raise ValueError("nominal_voltage_v must be > 0")
        if self.internal_resistance_ohm <= 0:
            raise ValueError("internal_resistance_ohm must be > 0")
        if self.max_continuous_a <= 0:
            raise ValueError("max_continuous_a must be > 0")
        if self.ocv_full_v <= self.ocv_empty_v:
            raise ValueError("ocv_full_v must be > ocv_empty_v")
        if self.cutoff_v <= 0:
            raise ValueError("cutoff_v must be > 0")

        if self.form_factor == "cylindrical":
            if (self.diameter_mm is None) or (self.height_mm is None):
                raise ValueError("cylindrical cells require diameter_mm and height_mm")
            if self.diameter_mm <= 0 or self.height_mm <= 0:
                raise ValueError("diameter_mm and height_mm must be > 0")
        elif self.form_factor == "prismatic":
            if None in (self.width_mm, self.length_mm, self.height_mm):
                raise ValueError("prismatic cells require width_mm, length_mm, height_mm")
            if (self.width_mm or 0) <= 0 or (self.length_mm or 0) <= 0 or (self.height_mm or 0) <= 0:
                raise ValueError("width_mm, length_mm, height_mm must be > 0")
        else:
            raise ValueError(f"Unknown form_factor: {self.form_factor!r}")


@dataclass(frozen=True)
class PackConfig:
    """Pack topology + layout."""

    series_s: int
    parallel_p: int

    # Layout: pack is visualized as a 3D grid of cells.
    rows: int
    cols: int
    layers: int = 1

    # Spacing between adjacent cells/blocks (edge-to-edge), in mm.
    spacing_mm: float = 2.0

    def validate(self) -> None:
        if self.series_s <= 0 or self.parallel_p <= 0:
            raise ValueError("series_s and parallel_p must be > 0")
        if self.rows <= 0 or self.cols <= 0 or self.layers <= 0:
            raise ValueError("rows, cols, layers must be > 0")
        if self.spacing_mm < 0:
            raise ValueError("spacing_mm must be >= 0")

    @property
    def cell_count(self) -> int:
        return self.series_s * self.parallel_p

    @property
    def capacity_slots(self) -> int:
        return self.rows * self.cols * self.layers


@dataclass(frozen=True)
class PackElectrical:
    nominal_voltage_v: float
    capacity_ah: float
    energy_wh_nominal: float
    internal_resistance_ohm: float
    max_continuous_a: float

    @staticmethod
    def from_cell_and_config(cell: CellSpec, cfg: PackConfig) -> "PackElectrical":
        cell.validate()
        cfg.validate()

        v_nom = cfg.series_s * cell.nominal_voltage_v
        cap_ah = cfg.parallel_p * cell.capacity_ah
        r_pack = (cfg.series_s * cell.internal_resistance_ohm) / cfg.parallel_p
        i_max = cfg.parallel_p * cell.max_continuous_a
        e_wh = v_nom * cap_ah
        return PackElectrical(
            nominal_voltage_v=v_nom,
            capacity_ah=cap_ah,
            energy_wh_nominal=e_wh,
            internal_resistance_ohm=r_pack,
            max_continuous_a=i_max,
        )

