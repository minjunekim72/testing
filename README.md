## Battery Cell Design Tool

Interactive battery cell early-design sandbox that:

- Generates **2D** (cross-section/footprint) and **3D** drawings (cylinder / prism)
- Estimates electrical properties:
  - **Capacity** (Ah)
  - **Nominal voltage** (V)
  - **Energy** (Wh)
  - **Energy density** (Wh/kg, Wh/L)
- Uses your **dimensions + materials + composition** (mass fractions, coating thickness, porosity, utilization)

This is a **first-order sizing model** meant for quick iteration, not a replacement for detailed electrochemical or manufacturing models.

### Quickstart

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

> If activation is blocked, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Windows (Command Prompt / cmd.exe)

```bat
py -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python run.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 run.py
```

Then open the Streamlit URL printed in the terminal.

### How the model works (high level)

- **Electrode capacity** is computed from:
  - coating thickness per side
  - porosity
  - mixture density from composition (active/binder/conductive)
  - active specific capacity (mAh/g)
  - utilization factor
- **Cell capacity** is the **minimum** of cathode and anode capacities.
- **Energy** = capacity (Ah) × nominal voltage (V)
- **Mass** includes coatings + current collectors + separator + electrolyte (rough fill model) + case (shell approximation)
- **Energy densities** computed from energy divided by mass and volume

### Project layout

- `app.py`: Streamlit UI
- `battery_cell_design_tool/`: calculation + geometry + visualization helpers
- `requirements.txt`: pinned Python dependencies
