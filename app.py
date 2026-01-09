from __future__ import annotations

import streamlit as st

from battery_cell_design_tool.calc import CellSpec, ElectrodeSpec, SeparatorSpec, compute_cell
from battery_cell_design_tool.geometry import CylindricalGeometry, PouchPrismaticGeometry
from battery_cell_design_tool.material_db import (
    ACTIVE_ANODES,
    ACTIVE_CATHODES,
    CASES,
    FOILS,
    INACTIVES,
)
from battery_cell_design_tool.viz2d import draw_2d_cylindrical, draw_2d_pouch
from battery_cell_design_tool.viz3d import draw_3d_cylindrical, draw_3d_pouch


st.set_page_config(page_title="Battery Cell Design Tool", layout="wide")

st.title("Battery Cell Design Tool")
st.caption(
    "Generates quick 2D/3D drawings and estimates capacity (Ah), voltage (V), energy (Wh), "
    "and gravimetric/volumetric energy density from geometry + materials/composition inputs."
)


def _number(label: str, value: float, *, min_value: float | None = None, step: float = 0.1, help: str | None = None):
    return st.number_input(label, value=value, min_value=min_value, step=step, help=help)


def _frac(label: str, value: float, help: str | None = None):
    return st.slider(label, min_value=0.0, max_value=1.0, value=float(value), step=0.01, help=help)


left, right = st.columns([1.0, 1.2], gap="large")

with left:
    st.subheader("Inputs")

    cell_type = st.selectbox("Cell type", ["Cylindrical", "Pouch/Prismatic"])

    st.markdown("#### Geometry")
    if cell_type == "Cylindrical":
        od_mm = _number("Outer diameter (mm)", 21.0, min_value=1.0, step=0.5)
        height_mm = _number("Height (mm)", 70.0, min_value=1.0, step=1.0)
        mandrel_mm = _number("Mandrel diameter (mm)", 4.0, min_value=0.0, step=0.5)
        geom_cyl = CylindricalGeometry(outer_diameter_mm=od_mm, height_mm=height_mm, mandrel_diameter_mm=mandrel_mm)
        geom_pouch = None
    else:
        width_mm = _number("Width (mm)", 60.0, min_value=1.0, step=1.0)
        height_mm = _number("Height (mm)", 100.0, min_value=1.0, step=1.0)
        thickness_mm = _number("Thickness (mm)", 10.0, min_value=0.5, step=0.5)
        margin_mm = _number("Inactive margin (mm)", 3.0, min_value=0.0, step=0.5, help="Edge margin excluded from active stack footprint.")
        geom_pouch = PouchPrismaticGeometry(width_mm=width_mm, height_mm=height_mm, thickness_mm=thickness_mm, margin_mm=margin_mm)
        geom_cyl = None

    st.markdown("#### Stack / layer model")
    unit_layer_thickness_um = _number(
        "Unit layer thickness (µm)",
        170.0,
        min_value=20.0,
        step=5.0,
        help="Approx. thickness per repeating unit: cathode+separator+anode+separator.",
    )
    pack_factor = _frac("Pack factor", 0.95, help="Accounts for tabs, gaps, and unusable volume inside the enclosure.")

    st.markdown("#### Cathode")
    cathode_active_name = st.selectbox("Cathode active material", list(ACTIVE_CATHODES.keys()), index=0)
    cathode_binder = st.selectbox("Cathode binder", list(INACTIVES.keys()), index=0)
    cathode_conductive = st.selectbox("Cathode conductive additive", list(INACTIVES.keys()), index=2)
    c_af = _frac("Cathode active mass fraction", 0.94)
    c_bf = _frac("Cathode binder mass fraction", 0.03)
    c_cf = max(0.0, 1.0 - c_af - c_bf)
    st.write(f"Cathode conductive mass fraction (auto): **{c_cf:.2f}**")
    c_th_um = _number("Cathode coating thickness per side (µm)", 70.0, min_value=1.0, step=1.0)
    c_por = _frac("Cathode porosity", 0.30)
    c_util = _frac("Cathode utilization", 0.95, help="Fraction of theoretical active capacity realized.")
    c_foil = st.selectbox("Cathode foil", list(FOILS.keys()), index=0)
    c_foil_um = _number("Cathode foil thickness (µm)", 15.0, min_value=1.0, step=1.0)

    st.markdown("#### Anode")
    anode_active_name = st.selectbox("Anode active material", list(ACTIVE_ANODES.keys()), index=0)
    anode_binder = st.selectbox("Anode binder", list(INACTIVES.keys()), index=1)
    anode_conductive = st.selectbox("Anode conductive additive", list(INACTIVES.keys()), index=2)
    a_af = _frac("Anode active mass fraction", 0.95)
    a_bf = _frac("Anode binder mass fraction", 0.03)
    a_cf = max(0.0, 1.0 - a_af - a_bf)
    st.write(f"Anode conductive mass fraction (auto): **{a_cf:.2f}**")
    a_th_um = _number("Anode coating thickness per side (µm)", 60.0, min_value=1.0, step=1.0)
    a_por = _frac("Anode porosity", 0.33)
    a_util = _frac("Anode utilization", 0.97)
    a_foil = st.selectbox("Anode foil", list(FOILS.keys()), index=1)
    a_foil_um = _number("Anode foil thickness (µm)", 10.0, min_value=1.0, step=1.0)

    st.markdown("#### Separator / Electrolyte / Case")
    sep_um = _number("Separator thickness (µm)", 20.0, min_value=1.0, step=1.0)
    elyte_fill = _frac("Electrolyte fill fraction", 0.85, help="Fraction of estimated void volume filled with electrolyte.")
    case_mat = st.selectbox("Case material", list(CASES.keys()), index=0)
    case_th_mm = _number("Case thickness (mm)", 0.30, min_value=0.05, step=0.05)

    st.markdown("#### Electrical")
    default_v = ACTIVE_CATHODES[cathode_active_name].typical_nominal_voltage_V
    nominal_v = _number(
        "Nominal voltage (V)",
        float(default_v),
        min_value=0.1,
        step=0.05,
        help="Default is a typical value for the chosen cathode paired with graphite; edit as needed.",
    )

with right:
    st.subheader("Outputs")

    cathode_spec = ElectrodeSpec(
        active_name=cathode_active_name,
        binder_name=cathode_binder,
        conductive_name=cathode_conductive,
        active_mass_fraction=c_af,
        binder_mass_fraction=c_bf,
        conductive_mass_fraction=c_cf,
        coating_thickness_um_per_side=c_th_um,
        porosity=c_por,
        utilization=c_util,
        foil_name=c_foil,
        foil_thickness_um=c_foil_um,
    )
    anode_spec = ElectrodeSpec(
        active_name=anode_active_name,
        binder_name=anode_binder,
        conductive_name=anode_conductive,
        active_mass_fraction=a_af,
        binder_mass_fraction=a_bf,
        conductive_mass_fraction=a_cf,
        coating_thickness_um_per_side=a_th_um,
        porosity=a_por,
        utilization=a_util,
        foil_name=a_foil,
        foil_thickness_um=a_foil_um,
    )

    spec = CellSpec(
        cell_type=cell_type,
        cylindrical=geom_cyl,
        pouch=geom_pouch,
        unit_layer_thickness_um=unit_layer_thickness_um,
        pack_factor=pack_factor,
        cathode=cathode_spec,
        anode=anode_spec,
        separator=SeparatorSpec(thickness_um=sep_um),
        electrolyte_fill_fraction=elyte_fill,
        nominal_voltage_V=nominal_v,
        case_material=case_mat,
        case_thickness_mm=case_th_mm,
    )

    try:
        cathode_active = ACTIVE_CATHODES[cathode_active_name]
        anode_active = ACTIVE_ANODES[anode_active_name]
        res = compute_cell(
            spec,
            cathode_active=(cathode_active.specific_capacity_mAh_g, cathode_active.density_g_cc),
            anode_active=(anode_active.specific_capacity_mAh_g, anode_active.density_g_cc),
        )

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Capacity", f"{res.capacity_Ah:.2f} Ah")
        m2.metric("Nominal voltage", f"{res.nominal_voltage_V:.2f} V")
        m3.metric("Energy", f"{res.energy_Wh:.1f} Wh")
        m4.metric("Energy density (Wh/kg)", f"{res.gravimetric_energy_density_Wh_kg:.0f}")
        m5.metric("Energy density (Wh/L)", f"{res.volumetric_energy_density_Wh_L:.0f}")

        st.caption(f"Limiting electrode: **{res.limiting_electrode}**")

        tab1, tab2, tab3 = st.tabs(["Drawings", "Breakdown", "Assumptions"])

        with tab1:
            c1, c2 = st.columns([1.0, 1.0], gap="large")
            with c1:
                st.markdown("**2D**")
                if cell_type == "Cylindrical":
                    st.pyplot(draw_2d_cylindrical(geom_cyl))
                else:
                    st.pyplot(draw_2d_pouch(geom_pouch))
            with c2:
                st.markdown("**3D**")
                if cell_type == "Cylindrical":
                    st.plotly_chart(draw_3d_cylindrical(geom_cyl), use_container_width=True)
                else:
                    st.plotly_chart(draw_3d_pouch(geom_pouch), use_container_width=True)

        with tab2:
            st.markdown("**Electrodes**")
            e1, e2 = st.columns(2)
            with e1:
                st.markdown("Cathode")
                st.write(
                    {
                        "Active mass (g)": round(res.cathode.active_mass_g, 2),
                        "Coating mass (g)": round(res.cathode.coating_mass_g, 2),
                        "Foil mass (g)": round(res.cathode.foil_mass_g, 2),
                        "Capacity (mAh)": round(res.cathode.capacity_mAh, 0),
                        "Areal capacity (mAh/cm²)": round(res.cathode.areal_capacity_mAh_cm2, 3),
                        "Coated area (cm², both sides)": round(res.cathode.coated_area_cm2_both_sides, 0),
                        "Sheets": res.cathode.n_sheets,
                    }
                )
            with e2:
                st.markdown("Anode")
                st.write(
                    {
                        "Active mass (g)": round(res.anode.active_mass_g, 2),
                        "Coating mass (g)": round(res.anode.coating_mass_g, 2),
                        "Foil mass (g)": round(res.anode.foil_mass_g, 2),
                        "Capacity (mAh)": round(res.anode.capacity_mAh, 0),
                        "Areal capacity (mAh/cm²)": round(res.anode.areal_capacity_mAh_cm2, 3),
                        "Coated area (cm², both sides)": round(res.anode.coated_area_cm2_both_sides, 0),
                        "Sheets": res.anode.n_sheets,
                    }
                )

            st.markdown("**Other masses**")
            st.write(
                {
                    "Separator mass (g)": round(res.separator_mass_g, 2),
                    "Electrolyte mass (g)": round(res.electrolyte_mass_g, 2),
                    "Case mass (g)": round(res.case_mass_g, 2),
                    "Total mass (kg)": round(res.mass_kg, 4),
                    "Stack volume (L)": round(res.volume_L, 4),
                }
            )

            if res.notes:
                st.markdown("**Notes**")
                for n in res.notes:
                    st.write(f"- {n}")

        with tab3:
            st.markdown(
                r"""
This tool uses a transparent, first-order model intended for early sizing:

- Capacity is computed from **active mass** in cathode/anode coatings (from thickness, porosity, and composition), then the cell capacity is the **minimum** of the two.
- Cylindrical jellyroll sheet length uses: \(L \\approx \\pi(R_o^2 - R_i^2) / t\\), where \(t\\) is the unit-layer thickness.
- Stack volume uses the **active stack volume** (geometry) times a **pack factor**.
- Electrolyte mass is estimated from coating porosity + remaining free volume and a user fill fraction.
- Case mass uses a simple shell approximation.

If you want a different formulation (tabs, headspace, detailed jellyroll layer counting, inactive component library, thermal model, etc.), the code is designed to be extended.
"""
            )

    except Exception as e:
        st.error(str(e))
        st.stop()

