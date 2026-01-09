from __future__ import annotations


def mm_to_cm(mm: float) -> float:
    return mm / 10.0


def um_to_cm(um: float) -> float:
    return um / 10_000.0


def cm2_to_m2(cm2: float) -> float:
    return cm2 / 10_000.0


def cm3_to_L(cm3: float) -> float:
    return cm3 / 1000.0


def g_to_kg(g: float) -> float:
    return g / 1000.0


def mAh_to_Ah(mAh: float) -> float:
    return mAh / 1000.0

