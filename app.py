from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from battery_tool.cad import EnclosureSpec, build_pack_scene_mm, export_scene_obj_bytes, export_scene_stl_bytes
from battery_tool.drawings import DrawingSpec, export_top_view_dxf_bytes, export_top_view_svg
from battery_tool.geometry import compute_pack_bounds_mm
from battery_tool.models import CellSpec, PackConfig, PackElectrical
from battery_tool.plotting import config_to_json, pack_3d_cad_figure, pack_3d_figure
from battery_tool.simulate import simulate_constant_current_discharge


st.set_page_config(page_title="Battery Builder", layout="wide")


def _format_seconds(seconds: float) -> str:
    if seconds <= 0 or math.isnan(seconds):
        return "0s"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _chart(df: pd.DataFrame, x: str, y: str, title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines", name=y))
    fig.update_layout(
        title=title,
        xaxis_title=x,
        yaxis_title=y_title,
        margin=dict(l=10, r=10, t=40, b=10),
        height=260,
    )
    return fig


st.title("Battery Builder (3D pack layout + basic electrical simulation)")
st.caption(
    "This is a lightweight engineering sketch tool (not CAD, not chemistry-accurate). "
    "It helps you visualize a pack arrangement and estimate voltage/current/power/energy under load."
)

with st.sidebar:
    st.header("Cell")
    preset = st.selectbox("Preset", ["18650 Li-ion (typical)", "Custom"], index=0)

    if preset == "18650 Li-ion (typical)":
        name = "18650 (typical)"
        form_factor = "cylindrical"
        nominal_voltage_v = 3.6
        capacity_ah = 3.0
        internal_resistance_ohm = 0.035
        max_continuous_a = 10.0
        ocv_full_v = 4.2
        ocv_empty_v = 3.0
        cutoff_v = 3.0
        diameter_mm = 18.0
        height_mm = 65.0
        width_mm = None
        length_mm = None
    else:
        name = st.text_input("Name", "Custom cell")
        form_factor = st.selectbox("Form factor", ["cylindrical", "prismatic"], index=0)
        nominal_voltage_v = st.number_input("Nominal voltage (V)", 0.1, 1000.0, 3.6, 0.1)
        capacity_ah = st.number_input("Capacity (Ah)", 0.01, 10000.0, 3.0, 0.1)
        internal_resistance_ohm = st.number_input("Internal resistance (Ω)", 0.0001, 10.0, 0.035, 0.001)
        max_continuous_a = st.number_input("Max continuous current (A)", 0.1, 10000.0, 10.0, 0.5)
        ocv_full_v = st.number_input("OCV full (V)", 0.1, 1000.0, 4.2, 0.05)
        ocv_empty_v = st.number_input("OCV empty (V)", 0.1, 1000.0, 3.0, 0.05)
        cutoff_v = st.number_input("Cutoff per-cell (V)", 0.1, 1000.0, 3.0, 0.05)

        diameter_mm = height_mm = width_mm = length_mm = None
        if form_factor == "cylindrical":
            diameter_mm = st.number_input("Diameter (mm)", 1.0, 500.0, 18.0, 1.0)
            height_mm = st.number_input("Height (mm)", 1.0, 500.0, 65.0, 1.0)
        else:
            width_mm = st.number_input("Width (mm)", 1.0, 1000.0, 30.0, 1.0)
            length_mm = st.number_input("Length (mm)", 1.0, 1000.0, 100.0, 1.0)
            height_mm = st.number_input("Height (mm)", 1.0, 1000.0, 10.0, 1.0)

    st.divider()
    st.header("Pack configuration")
    series_s = st.number_input("Series (S)", 1, 400, 10, 1)
    parallel_p = st.number_input("Parallel (P)", 1, 400, 4, 1)

    st.subheader("3D layout grid")
    cols = st.number_input("Columns", 1, 200, 10, 1)
    rows = st.number_input("Rows", 1, 200, 4, 1)
    layers = st.number_input("Layers", 1, 50, 1, 1)
    spacing_mm = st.number_input("Spacing between cells (mm)", 0.0, 50.0, 2.0, 0.5)

    st.divider()
    st.header("CAD / geometry")
    view_mode = st.selectbox("3D view mode", ["CAD solids", "Schematic"], index=0)
    enclosure_style = st.selectbox("Enclosure style", ["Battery case", "Simple box"], index=0)
    include_enclosure = st.checkbox("Include enclosure (outer block)", value=True)
    enclosure_clearance_mm = st.number_input("Enclosure clearance (mm)", 0.0, 50.0, 2.0, 0.5)
    enclosure_wall_mm = st.number_input("Enclosure wall thickness (mm)", 0.0, 50.0, 2.0, 0.5)
    mesh_sections = st.slider("Cylinder smoothness", 8, 64, 28, 2)

    st.divider()
    st.header("Use / load simulation")
    current_a = st.number_input("Constant current draw (A)", 0.1, 10000.0, 20.0, 0.5)
    initial_soc = st.slider("Initial SOC", 0.0, 1.0, 1.0, 0.01)
    dt_s = st.number_input("Simulation timestep (s)", 0.1, 60.0, 1.0, 0.5)


cell = CellSpec(
    name=name,
    nominal_voltage_v=float(nominal_voltage_v),
    capacity_ah=float(capacity_ah),
    internal_resistance_ohm=float(internal_resistance_ohm),
    max_continuous_a=float(max_continuous_a),
    ocv_full_v=float(ocv_full_v),
    ocv_empty_v=float(ocv_empty_v),
    cutoff_v=float(cutoff_v),
    form_factor=form_factor,
    diameter_mm=None if diameter_mm is None else float(diameter_mm),
    height_mm=None if height_mm is None else float(height_mm),
    width_mm=None if width_mm is None else float(width_mm),
    length_mm=None if length_mm is None else float(length_mm),
)

cfg = PackConfig(
    series_s=int(series_s),
    parallel_p=int(parallel_p),
    rows=int(rows),
    cols=int(cols),
    layers=int(layers),
    spacing_mm=float(spacing_mm),
)

errors: list[str] = []
try:
    cell.validate()
    cfg.validate()
except Exception as e:  # noqa: BLE001 - Streamlit UX: show error text
    errors.append(str(e))

if cfg.cell_count > cfg.capacity_slots:
    errors.append(
        f"Layout grid has {cfg.capacity_slots} slots, but S×P needs {cfg.cell_count} cells. "
        "Increase rows/cols/layers or reduce S/P."
    )

if errors:
    st.error("Fix configuration issues:\n- " + "\n- ".join(errors))
    st.stop()


elec = PackElectrical.from_cell_and_config(cell, cfg)
bounds = compute_pack_bounds_mm(cell, cfg)

col_a, col_b, col_c = st.columns([1.15, 1.15, 1.0], gap="large")

with col_a:
    st.subheader("3D pack layout")
    if view_mode == "CAD solids":
        style_key = "battery_case" if enclosure_style == "Battery case" else "box"
        fig3d = pack_3d_cad_figure(
            cell,
            cfg,
            include_enclosure=include_enclosure,
            enclosure_style=style_key,
            enclosure_clearance_mm=float(enclosure_clearance_mm),
            enclosure_wall_mm=float(enclosure_wall_mm),
            mesh_sections=int(mesh_sections),
        )
    else:
        highlight_n = min(cfg.cell_count, cfg.capacity_slots)
        fig3d = pack_3d_figure(cell, cfg, highlight_n=highlight_n)

    st.plotly_chart(fig3d, width="stretch")

with col_b:
    st.subheader("Electrical properties (basic)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Nominal voltage", f"{elec.nominal_voltage_v:.2f} V")
    m2.metric("Capacity", f"{elec.capacity_ah:.2f} Ah")
    m3.metric("Nominal energy", f"{elec.energy_wh_nominal:.1f} Wh")

    m4, m5, m6 = st.columns(3)
    m4.metric("Pack internal resistance", f"{elec.internal_resistance_ohm:.4f} Ω")
    m5.metric("Max continuous current", f"{elec.max_continuous_a:.1f} A")
    m6.metric("Cell count", f"{cfg.cell_count} cells")

    st.caption(
        "Rule-of-thumb check: try to keep your requested current below max continuous. "
        "This model does not include temperature, aging, BMS limits, or voltage sag vs SOC."
    )

    if current_a > elec.max_continuous_a:
        st.warning(
            f"Requested current ({current_a:.1f} A) exceeds max continuous estimate "
            f"({elec.max_continuous_a:.1f} A)."
        )

    # Quick at-SOC estimates
    soc_probe = float(initial_soc)
    ocv_cell = cell.ocv_empty_v + soc_probe * (cell.ocv_full_v - cell.ocv_empty_v)
    ocv_pack = cfg.series_s * ocv_cell
    v_term = ocv_pack - float(current_a) * elec.internal_resistance_ohm
    st.write(
        f"At SOC={soc_probe:.2f} and {current_a:.1f}A: "
        f"OCV≈**{ocv_pack:.2f}V**, terminal≈**{v_term:.2f}V**, power≈**{(v_term*current_a):.0f}W**"
    )

    st.subheader("Pack size (bounding box)")
    st.write(
        f"X: **{(bounds.x_max - bounds.x_min):.1f} mm**, "
        f"Y: **{(bounds.y_max - bounds.y_min):.1f} mm**, "
        f"Z: **{(bounds.z_max - bounds.z_min):.1f} mm**"
    )

with col_c:
    st.subheader("CAD exports (2D + 3D)")

    export_name = f"{cell.name.replace(' ', '_')}_{cfg.series_s}S{cfg.parallel_p}P"
    enclosure_spec = EnclosureSpec(
        include=bool(include_enclosure),
        style="battery_case" if enclosure_style == "Battery case" else "box",
        clearance_mm=float(enclosure_clearance_mm),
        wall_mm=float(enclosure_wall_mm),
    )
    drawing_spec = DrawingSpec(
        include_enclosure_outline=bool(include_enclosure),
        enclosure_clearance_mm=float(enclosure_clearance_mm),
        enclosure_wall_mm=float(enclosure_wall_mm),
    )

    @st.cache_data(show_spinner=False)
    def _exports(
        _cell: CellSpec,
        _cfg: PackConfig,
        _enclosure: EnclosureSpec,
        _mesh_sections: int,
        _drawing: DrawingSpec,
    ) -> dict[str, bytes | str]:
        scene = build_pack_scene_mm(_cell, _cfg, sections=int(_mesh_sections), enclosure=_enclosure)
        return {
            "config_json": config_to_json(_cell, _cfg),
            "stl": export_scene_stl_bytes(scene),
            "obj": export_scene_obj_bytes(scene),
            "svg_top": export_top_view_svg(_cell, _cfg, spec=_drawing),
            "dxf_top": export_top_view_dxf_bytes(_cell, _cfg, spec=_drawing),
        }

    exp = _exports(cell, cfg, enclosure_spec, int(mesh_sections), drawing_spec)

    st.download_button(
        "Download 3D STL",
        data=exp["stl"],
        file_name=f"{export_name}.stl",
        mime="model/stl",
        use_container_width=True,
    )
    st.download_button(
        "Download 3D OBJ",
        data=exp["obj"],
        file_name=f"{export_name}.obj",
        mime="text/plain",
        use_container_width=True,
    )
    st.download_button(
        "Download 2D SVG (top view)",
        data=exp["svg_top"],
        file_name=f"{export_name}_top.svg",
        mime="image/svg+xml",
        use_container_width=True,
    )
    st.download_button(
        "Download 2D DXF (top view)",
        data=exp["dxf_top"],
        file_name=f"{export_name}_top.dxf",
        mime="application/dxf",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Configuration (JSON)")
    st.code(exp["config_json"], language="json")


st.divider()
st.subheader("In-use simulation (constant-current discharge)")

df = simulate_constant_current_discharge(
    cell=cell,
    cfg=cfg,
    current_a=float(current_a),
    initial_soc=float(initial_soc),
    dt_s=float(dt_s),
)

if len(df) >= 2:
    runtime_s = float(df["time_s"].iloc[-1])
    e_used = float(df["energy_wh_used"].iloc[-1])
    v_min = float(df["pack_v_v"].min())
    v_max = float(df["pack_v_v"].max())

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Runtime to cutoff", _format_seconds(runtime_s))
    s2.metric("Energy delivered", f"{e_used:.1f} Wh")
    s3.metric("Voltage range", f"{v_min:.1f}–{v_max:.1f} V")
    s4.metric("Avg power", f"{(e_used / (runtime_s / 3600.0)):.0f} W" if runtime_s > 0 else "—")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(_chart(df, "time_s", "pack_v_v", "Terminal voltage vs time", "V"), width="stretch")
    with c2:
        st.plotly_chart(_chart(df, "time_s", "soc", "SOC vs time", "SOC"), width="stretch")
    with c3:
        st.plotly_chart(_chart(df, "time_s", "pack_p_w", "Power vs time", "W"), width="stretch")

    with st.expander("Raw simulation table"):
        st.dataframe(df, use_container_width=True, height=240)
else:
    st.info("Simulation produced no data (check your inputs).")

