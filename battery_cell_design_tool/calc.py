from __future__ import annotations

import math
from dataclasses import dataclass

from .geometry import CylindricalGeometry, PouchPrismaticGeometry
from .material_db import CASES, ELECTROLYTE_DENSITY_G_CC, FOILS, INACTIVES, SEPARATOR_DENSITY_G_CC
from .units import cm3_to_L, g_to_kg, mAh_to_Ah, mm_to_cm, um_to_cm


def _validate_fraction(name: str, x: float) -> None:
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"{name} must be between 0 and 1.")


def mixture_density_g_cc(*, mass_fractions: dict[str, float], densities_g_cc: dict[str, float]) -> float:
    """
    Effective density assuming ideal volume additivity:
      1/rho = sum_i (w_i / rho_i)
    """
    s = 0.0
    for k, w in mass_fractions.items():
        if k not in densities_g_cc:
            raise ValueError(f"Missing density for {k}")
        if w < 0:
            raise ValueError("Mass fractions must be non-negative.")
        s += w / densities_g_cc[k]
    if s <= 0:
        raise ValueError("Invalid mixture fractions; sum must be > 0.")
    return 1.0 / s


@dataclass(frozen=True)
class ElectrodeSpec:
    active_name: str
    binder_name: str
    conductive_name: str

    active_mass_fraction: float
    binder_mass_fraction: float
    conductive_mass_fraction: float

    coating_thickness_um_per_side: float
    porosity: float
    utilization: float

    foil_name: str
    foil_thickness_um: float

    def validate(self) -> None:
        _validate_fraction("active_mass_fraction", self.active_mass_fraction)
        _validate_fraction("binder_mass_fraction", self.binder_mass_fraction)
        _validate_fraction("conductive_mass_fraction", self.conductive_mass_fraction)
        if abs((self.active_mass_fraction + self.binder_mass_fraction + self.conductive_mass_fraction) - 1.0) > 1e-6:
            raise ValueError("Electrode mass fractions must sum to 1.0.")
        if self.coating_thickness_um_per_side <= 0:
            raise ValueError("Coating thickness must be > 0.")
        _validate_fraction("porosity", self.porosity)
        _validate_fraction("utilization", self.utilization)
        if self.foil_thickness_um <= 0:
            raise ValueError("Foil thickness must be > 0.")


@dataclass(frozen=True)
class SeparatorSpec:
    thickness_um: float

    def validate(self) -> None:
        if self.thickness_um <= 0:
            raise ValueError("Separator thickness must be > 0.")


@dataclass(frozen=True)
class CellSpec:
    cell_type: str  # "Cylindrical" or "Pouch/Prismatic"
    cylindrical: CylindricalGeometry | None
    pouch: PouchPrismaticGeometry | None

    # stack model
    unit_layer_thickness_um: float  # (cathode+sep+anode+sep) radial/stack build per unit
    pack_factor: float  # accounts for tabs, gaps, etc.

    cathode: ElectrodeSpec
    anode: ElectrodeSpec
    separator: SeparatorSpec

    electrolyte_fill_fraction: float  # fraction of remaining void volume filled

    nominal_voltage_V: float

    # casing / enclosure
    case_material: str
    case_thickness_mm: float

    def validate(self) -> None:
        if self.cell_type not in {"Cylindrical", "Pouch/Prismatic"}:
            raise ValueError("cell_type must be Cylindrical or Pouch/Prismatic.")
        if self.cell_type == "Cylindrical":
            if self.cylindrical is None:
                raise ValueError("cylindrical geometry required.")
            self.cylindrical.validate()
        else:
            if self.pouch is None:
                raise ValueError("pouch/prismatic geometry required.")
            self.pouch.validate()

        if self.unit_layer_thickness_um <= 0:
            raise ValueError("unit_layer_thickness_um must be > 0.")
        _validate_fraction("pack_factor", self.pack_factor)
        if self.pack_factor <= 0:
            raise ValueError("pack_factor must be > 0.")
        self.cathode.validate()
        self.anode.validate()
        self.separator.validate()
        _validate_fraction("electrolyte_fill_fraction", self.electrolyte_fill_fraction)
        if self.nominal_voltage_V <= 0:
            raise ValueError("nominal_voltage_V must be > 0.")
        if self.case_material not in CASES:
            raise ValueError("Unknown case material.")
        if self.case_thickness_mm <= 0:
            raise ValueError("case_thickness_mm must be > 0.")


@dataclass(frozen=True)
class ElectrodeResult:
    active_mass_g: float
    coating_mass_g: float
    foil_mass_g: float
    capacity_mAh: float
    areal_capacity_mAh_cm2: float
    coated_area_cm2_both_sides: float
    n_sheets: int


@dataclass(frozen=True)
class CellResult:
    capacity_Ah: float
    nominal_voltage_V: float
    energy_Wh: float
    mass_kg: float
    volume_L: float
    gravimetric_energy_density_Wh_kg: float
    volumetric_energy_density_Wh_L: float

    limiting_electrode: str

    cathode: ElectrodeResult
    anode: ElectrodeResult

    separator_mass_g: float
    electrolyte_mass_g: float
    case_mass_g: float

    notes: list[str]


def _sheet_area_one_side_cm2(spec: CellSpec) -> float:
    if spec.cell_type == "Cylindrical":
        assert spec.cylindrical is not None
        # For the jellyroll, the sheet "height" is cell height (ignores headspace/tabs).
        return spec.cylindrical.height_cm * 100.0  # placeholder; overridden via length-based model below
    assert spec.pouch is not None
    return spec.pouch.footprint_area_cm2()


def _jellyroll_length_cm(*, geom: CylindricalGeometry, unit_layer_thickness_um: float) -> tuple[float, int]:
    """
    Approximate total sheet length for a spiral jellyroll:
      L ≈ π*(R_out^2 - R_in^2) / t
    where t is the unit layer thickness (cm).
    """
    t_cm = um_to_cm(unit_layer_thickness_um)
    ro = geom.outer_radius_cm
    ri = geom.inner_radius_cm
    if t_cm <= 0:
        raise ValueError("unit layer thickness must be > 0.")
    if ro <= ri:
        return 0.0, 0
    n_units = int(math.floor((ro - ri) / t_cm))
    if n_units <= 0:
        return 0.0, 0
    L_cm = math.pi * (ro * ro - ri * ri) / t_cm
    return L_cm, n_units


def _compute_electrode(
    *,
    spec: CellSpec,
    electrode: ElectrodeSpec,
    active_specific_capacity_mAh_g: float,
    active_density_g_cc: float,
    n_sheets: int,
    sheet_area_one_side_cm2: float,
) -> ElectrodeResult:
    densities = {
        electrode.active_name: active_density_g_cc,
        electrode.binder_name: INACTIVES[electrode.binder_name].density_g_cc,
        electrode.conductive_name: INACTIVES[electrode.conductive_name].density_g_cc,
    }
    mass_fracs = {
        electrode.active_name: electrode.active_mass_fraction,
        electrode.binder_name: electrode.binder_mass_fraction,
        electrode.conductive_name: electrode.conductive_mass_fraction,
    }
    rho_solid = mixture_density_g_cc(mass_fractions=mass_fracs, densities_g_cc=densities)
    t_coat_cm = um_to_cm(electrode.coating_thickness_um_per_side)

    coated_area_cm2_both_sides = n_sheets * sheet_area_one_side_cm2 * 2.0
    coating_volume_cm3 = coated_area_cm2_both_sides * t_coat_cm
    coating_mass_g = coating_volume_cm3 * (1.0 - electrode.porosity) * rho_solid
    active_mass_g = coating_mass_g * electrode.active_mass_fraction

    capacity_mAh = active_mass_g * active_specific_capacity_mAh_g * electrode.utilization

    areal_capacity_mAh_cm2 = (
        (t_coat_cm * (1.0 - electrode.porosity) * rho_solid) * electrode.active_mass_fraction * active_specific_capacity_mAh_g * electrode.utilization
    )

    foil = FOILS[electrode.foil_name]
    foil_t_cm = um_to_cm(electrode.foil_thickness_um)
    foil_volume_cm3 = (n_sheets * sheet_area_one_side_cm2) * foil_t_cm
    foil_mass_g = foil_volume_cm3 * foil.density_g_cc

    return ElectrodeResult(
        active_mass_g=active_mass_g,
        coating_mass_g=coating_mass_g,
        foil_mass_g=foil_mass_g,
        capacity_mAh=capacity_mAh,
        areal_capacity_mAh_cm2=areal_capacity_mAh_cm2,
        coated_area_cm2_both_sides=coated_area_cm2_both_sides,
        n_sheets=n_sheets,
    )


def _compute_case_mass_g(*, spec: CellSpec, stack_volume_cm3: float) -> float:
    # Simple enclosure model: casing volume = stack_volume * (case_thickness / characteristic_dim)
    # This is intentionally rough; user can refine by editing.
    case = CASES[spec.case_material]
    t_cm = mm_to_cm(spec.case_thickness_mm)

    if spec.cell_type == "Cylindrical":
        assert spec.cylindrical is not None
        ro = spec.cylindrical.outer_radius_cm
        h = spec.cylindrical.height_cm
        r_can = ro + t_cm
        can_vol_cm3 = math.pi * (r_can * r_can - ro * ro) * h + math.pi * (r_can * r_can) * t_cm * 2.0
        return can_vol_cm3 * case.density_g_cc

    assert spec.pouch is not None
    w = spec.pouch.width_cm
    h = spec.pouch.height_cm
    th = spec.pouch.thickness_cm
    # box shell approximation
    outer_w = w + 2.0 * t_cm
    outer_h = h + 2.0 * t_cm
    outer_t = th + 2.0 * t_cm
    outer_vol = outer_w * outer_h * outer_t
    inner_vol = w * h * th
    shell_vol = max(0.0, outer_vol - inner_vol)
    return shell_vol * case.density_g_cc


def compute_cell(spec: CellSpec, *, cathode_active: tuple[float, float], anode_active: tuple[float, float]) -> CellResult:
    """
    cathode_active: (specific_capacity_mAh_g, density_g_cc)
    anode_active: (specific_capacity_mAh_g, density_g_cc)
    """
    spec.validate()
    notes: list[str] = []

    # Geometry + sheet sizing
    if spec.cell_type == "Cylindrical":
        assert spec.cylindrical is not None
        L_cm, n_units = _jellyroll_length_cm(geom=spec.cylindrical, unit_layer_thickness_um=spec.unit_layer_thickness_um)
        if n_units <= 0 or L_cm <= 0:
            raise ValueError("Computed 0 layers; increase OD/ decrease mandrel or unit-layer thickness.")
        # For simplicity, assume one cathode foil and one anode foil each spanning the full jellyroll length.
        n_cathode_sheets = n_units
        n_anode_sheets = n_units
        sheet_area_one_side_cm2 = spec.cylindrical.height_cm * L_cm
        sep_sheets = n_units * 2
        separator_area_cm2 = sep_sheets * sheet_area_one_side_cm2
        stack_volume_cm3 = spec.cylindrical.stack_volume_cm3() * spec.pack_factor
        notes.append(f"Jellyroll approximation: length≈{L_cm/100:.2f} m, units={n_units}.")
    else:
        assert spec.pouch is not None
        stack_volume_cm3 = spec.pouch.stack_volume_cm3() * spec.pack_factor
        t_unit_cm = um_to_cm(spec.unit_layer_thickness_um)
        if t_unit_cm <= 0:
            raise ValueError("unit_layer_thickness_um must be > 0.")
        n_units = int(math.floor(spec.pouch.thickness_cm / t_unit_cm))
        if n_units <= 0:
            raise ValueError("Computed 0 layers; increase thickness or decrease unit-layer thickness.")
        # Typical stacked pouch: cathode and anode count ~ n_units
        n_cathode_sheets = n_units
        n_anode_sheets = n_units
        sheet_area_one_side_cm2 = spec.pouch.footprint_area_cm2()
        sep_sheets = n_units * 2
        separator_area_cm2 = sep_sheets * sheet_area_one_side_cm2
        notes.append(f"Stack approximation: units={n_units}, footprint={sheet_area_one_side_cm2:.0f} cm².")

    cathode = _compute_electrode(
        spec=spec,
        electrode=spec.cathode,
        active_specific_capacity_mAh_g=cathode_active[0],
        active_density_g_cc=cathode_active[1],
        n_sheets=n_cathode_sheets,
        sheet_area_one_side_cm2=sheet_area_one_side_cm2,
    )
    anode = _compute_electrode(
        spec=spec,
        electrode=spec.anode,
        active_specific_capacity_mAh_g=anode_active[0],
        active_density_g_cc=anode_active[1],
        n_sheets=n_anode_sheets,
        sheet_area_one_side_cm2=sheet_area_one_side_cm2,
    )

    limiting = "Cathode" if cathode.capacity_mAh <= anode.capacity_mAh else "Anode"
    cell_capacity_Ah = mAh_to_Ah(min(cathode.capacity_mAh, anode.capacity_mAh))
    energy_Wh = cell_capacity_Ah * spec.nominal_voltage_V

    # Separator mass
    sep_t_cm = um_to_cm(spec.separator.thickness_um)
    separator_vol_cm3 = separator_area_cm2 * sep_t_cm
    separator_mass_g = separator_vol_cm3 * SEPARATOR_DENSITY_G_CC

    # Electrolyte mass: fill a fraction of voids inside coatings + remaining stack slack
    # (very rough; designed to be transparent & editable)
    coating_total_volume_cm3 = (
        (cathode.coated_area_cm2_both_sides * um_to_cm(spec.cathode.coating_thickness_um_per_side))
        + (anode.coated_area_cm2_both_sides * um_to_cm(spec.anode.coating_thickness_um_per_side))
    )
    void_in_coatings_cm3 = (
        cathode.coated_area_cm2_both_sides * um_to_cm(spec.cathode.coating_thickness_um_per_side) * spec.cathode.porosity
        + anode.coated_area_cm2_both_sides * um_to_cm(spec.anode.coating_thickness_um_per_side) * spec.anode.porosity
    )
    free_volume_cm3 = max(0.0, stack_volume_cm3 - coating_total_volume_cm3)
    electrolyte_vol_cm3 = spec.electrolyte_fill_fraction * (void_in_coatings_cm3 + 0.5 * free_volume_cm3)
    electrolyte_mass_g = electrolyte_vol_cm3 * ELECTROLYTE_DENSITY_G_CC

    # Case mass
    case_mass_g = _compute_case_mass_g(spec=spec, stack_volume_cm3=stack_volume_cm3)

    total_mass_g = (
        cathode.coating_mass_g
        + cathode.foil_mass_g
        + anode.coating_mass_g
        + anode.foil_mass_g
        + separator_mass_g
        + electrolyte_mass_g
        + case_mass_g
    )

    mass_kg = g_to_kg(total_mass_g)
    volume_L = cm3_to_L(stack_volume_cm3)
    if mass_kg <= 0 or volume_L <= 0:
        raise ValueError("Computed non-positive mass or volume; check inputs.")

    return CellResult(
        capacity_Ah=cell_capacity_Ah,
        nominal_voltage_V=spec.nominal_voltage_V,
        energy_Wh=energy_Wh,
        mass_kg=mass_kg,
        volume_L=volume_L,
        gravimetric_energy_density_Wh_kg=energy_Wh / mass_kg,
        volumetric_energy_density_Wh_L=energy_Wh / volume_L,
        limiting_electrode=limiting,
        cathode=cathode,
        anode=anode,
        separator_mass_g=separator_mass_g,
        electrolyte_mass_g=electrolyte_mass_g,
        case_mass_g=case_mass_g,
        notes=notes,
    )

