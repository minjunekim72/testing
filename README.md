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

**Recommended Python version**: **Python 3.12** (Windows-friendly wheels are widely available).  
Python **3.14** on Windows may fail to install dependencies because some packages may not ship wheels yet, causing pip to try (and fail) source builds.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

> If activation is blocked, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Windows (Command Prompt / cmd.exe)

```bat
py -3.12 -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python run.py
```

### Windows (Git Bash / MSYS2 bash)

```bash
py -3.12 -m venv .venv
source .venv/Scripts/activate
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

### Desktop shortcut (Windows)

If you want a “double click to launch” experience on Windows:

- Double-click `start_windows.bat` from the project folder, **or**
- Create a Desktop shortcut to `start_windows.bat`:
  - Right click `start_windows.bat` → **Show more options** → **Send to** → **Desktop (create shortcut)**

The script will create/use `.venv`, install requirements, and start the app at `http://localhost:8501`.

### Troubleshooting install errors (Windows)

If you see `No module named streamlit` or pip build errors, first confirm you’re installing into the venv:

```bat
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
```

If it still fails, please share the **full pip error output** and the output of:

```bat
py -V
py -m pip -V
```

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
