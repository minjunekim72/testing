from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveMaterial:
    name: str
    specific_capacity_mAh_g: float
    density_g_cc: float
    # Typical nominal cell voltage when paired with graphite (very rough, editable)
    typical_nominal_voltage_V: float


@dataclass(frozen=True)
class InactiveMaterial:
    name: str
    density_g_cc: float


@dataclass(frozen=True)
class FoilMaterial:
    name: str
    density_g_cc: float


@dataclass(frozen=True)
class CaseMaterial:
    name: str
    density_g_cc: float


ACTIVE_CATHODES: dict[str, ActiveMaterial] = {
    "NMC811": ActiveMaterial("NMC811", specific_capacity_mAh_g=200.0, density_g_cc=4.8, typical_nominal_voltage_V=3.7),
    "NMC622": ActiveMaterial("NMC622", specific_capacity_mAh_g=180.0, density_g_cc=4.7, typical_nominal_voltage_V=3.65),
    "NCA": ActiveMaterial("NCA", specific_capacity_mAh_g=200.0, density_g_cc=4.8, typical_nominal_voltage_V=3.7),
    "LFP": ActiveMaterial("LFP", specific_capacity_mAh_g=160.0, density_g_cc=3.6, typical_nominal_voltage_V=3.2),
    "LMO": ActiveMaterial("LMO", specific_capacity_mAh_g=110.0, density_g_cc=4.3, typical_nominal_voltage_V=3.9),
}

ACTIVE_ANODES: dict[str, ActiveMaterial] = {
    "Graphite": ActiveMaterial("Graphite", specific_capacity_mAh_g=350.0, density_g_cc=2.2, typical_nominal_voltage_V=0.0),
    "Si-Graphite (10% Si)": ActiveMaterial("Si-Graphite (10% Si)", specific_capacity_mAh_g=600.0, density_g_cc=2.3, typical_nominal_voltage_V=0.0),
    "LTO": ActiveMaterial("LTO", specific_capacity_mAh_g=160.0, density_g_cc=3.5, typical_nominal_voltage_V=0.0),
}

INACTIVES: dict[str, InactiveMaterial] = {
    "PVDF binder": InactiveMaterial("PVDF binder", density_g_cc=1.8),
    "CMC/SBR binder": InactiveMaterial("CMC/SBR binder", density_g_cc=1.4),
    "Carbon black": InactiveMaterial("Carbon black", density_g_cc=1.9),
}

FOILS: dict[str, FoilMaterial] = {
    "Al (cathode current collector)": FoilMaterial("Al (cathode current collector)", density_g_cc=2.70),
    "Cu (anode current collector)": FoilMaterial("Cu (anode current collector)", density_g_cc=8.96),
}

SEPARATOR_DENSITY_G_CC = 0.90  # polymer separator bulk density (rough)
ELECTROLYTE_DENSITY_G_CC = 1.20

CASES: dict[str, CaseMaterial] = {
    "Aluminum": CaseMaterial("Aluminum", density_g_cc=2.70),
    "Steel": CaseMaterial("Steel", density_g_cc=7.85),
}

