# PyLite DSA Workspace

A lightweight, Python-only IDE for learning Python, algorithms, and data structures with a minimalist glassmorphic UI.

## Features

- Minimal dual-icon topbar (`☰` menu + `📝` notebook)
- Compact Python tab workspace with close controls
- Python-only file tree (`.py` files)
- Full file run, run selection, and instant stop
- Live mode: auto-runs saved files and clears output when editor is emptied
- Right-click contextual actions:
  - Run Selection
  - Save as Note
  - Stop
  - Toggle Live Mode
- Clean output panel for Python stdout/stderr only
- DSA notebook drawer with:
  - Categories
  - Section isolation + expand all
  - Run note code
  - Save note output
  - Insert note into editor
- Background customization:
  - Solid dark mode
  - Wallpaper mode with custom upload

## Tech Stack

- Frontend: HTML, CSS, Vanilla JavaScript
- Backend: Python 3.10+, Flask

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app
```

Open: `http://localhost:5000`

## Notes

- This workspace intentionally supports **Python only**.
- Notebook data is stored in `notebook_data.json`.
