## Battery Builder (3D design + basic electrical properties)

This repo contains a small interactive tool that lets you:

- **Design a battery pack**: choose a cell spec and pack topology (S/P) and a 3D grid layout.
- **Visualize the pack in 3D**: a schematic 3D view of cell placement and overall bounds.
- **See basic electrical properties while “in use”**: voltage/current/power/energy estimates under a constant-current discharge simulation.

### Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

### What’s included

- **UI**: `app.py` (Streamlit)
- **Core logic**: `battery_tool/`
  - `models.py`: cell + pack specs and pack-level electrical aggregation
  - `geometry.py`: 3D cell grid center generation + pack bounds
  - `simulate.py`: constant-current discharge simulation
  - `plotting.py`: Plotly 3D visualization helpers

### Important limitations (read this)

This is a **concept / sizing tool**. It is *not* CAD, and the electrical model is intentionally simple:

- OCV vs SOC is **linear** (real cells are not).
- Internal resistance is a **single constant** (no SOC/temperature dependence).
- No thermal model, aging model, BMS limits, balancing, wiring/busbar resistance, contact resistance, etc.

If you want, I can extend it with:

- Realistic OCV curves (CSV per chemistry), Peukert-like behavior, temperature effects
- Basic BMS constraints, voltage sag vs SOC, charge simulation
- More detailed 3D geometry (cell cylinders/prisms, busbars), export (STEP/OBJ/STL)
