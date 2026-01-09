from __future__ import annotations

import math
from dataclasses import dataclass

from .units import mm_to_cm


@dataclass(frozen=True)
class CylindricalGeometry:
    outer_diameter_mm: float
    height_mm: float
    mandrel_diameter_mm: float

    def validate(self) -> None:
        if self.outer_diameter_mm <= 0 or self.height_mm <= 0:
            raise ValueError("Outer diameter and height must be > 0.")
        if self.mandrel_diameter_mm < 0:
            raise ValueError("Mandrel diameter must be >= 0.")
        if self.mandrel_diameter_mm >= self.outer_diameter_mm:
            raise ValueError("Mandrel diameter must be smaller than outer diameter.")

    @property
    def outer_radius_cm(self) -> float:
        return mm_to_cm(self.outer_diameter_mm) / 2.0

    @property
    def inner_radius_cm(self) -> float:
        return mm_to_cm(self.mandrel_diameter_mm) / 2.0

    @property
    def height_cm(self) -> float:
        return mm_to_cm(self.height_mm)

    def stack_cross_section_area_cm2(self) -> float:
        ro = self.outer_radius_cm
        ri = self.inner_radius_cm
        return math.pi * (ro * ro - ri * ri)

    def stack_volume_cm3(self) -> float:
        return self.stack_cross_section_area_cm2() * self.height_cm


@dataclass(frozen=True)
class PouchPrismaticGeometry:
    width_mm: float
    height_mm: float
    thickness_mm: float
    margin_mm: float

    def validate(self) -> None:
        if self.width_mm <= 0 or self.height_mm <= 0 or self.thickness_mm <= 0:
            raise ValueError("Width, height, thickness must be > 0.")
        if self.margin_mm < 0:
            raise ValueError("Margin must be >= 0.")
        if self.margin_mm * 2.0 >= min(self.width_mm, self.height_mm):
            raise ValueError("Margin is too large for the given width/height.")

    @property
    def width_cm(self) -> float:
        return mm_to_cm(self.width_mm)

    @property
    def height_cm(self) -> float:
        return mm_to_cm(self.height_mm)

    @property
    def thickness_cm(self) -> float:
        return mm_to_cm(self.thickness_mm)

    @property
    def margin_cm(self) -> float:
        return mm_to_cm(self.margin_mm)

    def footprint_area_cm2(self) -> float:
        w = self.width_cm - 2.0 * self.margin_cm
        h = self.height_cm - 2.0 * self.margin_cm
        return w * h

    def stack_volume_cm3(self) -> float:
        return self.footprint_area_cm2() * self.thickness_cm

