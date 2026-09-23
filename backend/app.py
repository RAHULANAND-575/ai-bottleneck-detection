"""Flask app for a lightweight Python IDE + DSA notebook."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import safe_join

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BASE_DIR
NOTEBOOK_DB = BASE_DIR / "notebook_data.json"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)

run_lock = threading.Lock()
runs: dict[str, dict] = {}


def ok(data):
    return jsonify({"status": "ok", "data": data})


def err(message, code=400):
    return jsonify({"status": "error", "message": str(message)}), code


def safe_rel_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Path is required")
    joined = safe_join(str(WORKSPACE_ROOT), raw_path)
    if not joined:
        raise ValueError("Invalid path")
    resolved = Path(joined).resolve()
    if resolved.suffix != ".py":
        raise ValueError("Only Python files are supported")
    try:
        resolved.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Invalid path") from exc
    if not resolved.name:
        raise ValueError("Invalid path")
    return resolved


def build_tree(directory: Path, rel_prefix: Path = Path("")):
    children = []
    for item in sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        if item.name.startswith(".") or item.name in {"__pycache__", "node_modules"}:
            continue
        rel_path = rel_prefix / item.name
        if item.is_dir():
            node = build_tree(item, rel_path)
            if node["children"]:
                children.append(node)
        elif item.suffix == ".py":
            children.append({"type": "file", "name": item.name, "path": rel_path.as_posix()})

    return {
        "type": "folder",
        "name": "MyProject" if rel_prefix == Path("") else directory.name,
        "path": rel_prefix.as_posix(),
        "children": children,
    }


def load_notebook() -> dict:
    if not NOTEBOOK_DB.exists():
        seed = {
            "categories": [
                {
                    "name": "Sorting Algorithms",
                    "notes": [],
                }
            ]
        }
        NOTEBOOK_DB.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return seed

    try:
        return json.loads(NOTEBOOK_DB.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"categories": []}


def save_notebook(data: dict):
    NOTEBOOK_DB.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_worker(run_id: str, code: str):
    run = runs[run_id]
    proc = subprocess.Popen(
        ["python", "-u", "-c", code],
        cwd=str(WORKSPACE_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    run["process"] = proc

    lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            run["output"] = "".join(lines)
        proc.wait()
        if run["status"] == "stopped":
            run["output"] = "".join(lines)
        elif proc.returncode == 0:
            run["status"] = "finished"
            run["output"] = "".join(lines) or "Run completed: Success\n"
        else:
            run["status"] = "error"
            run["output"] = "".join(lines) or f"Process exited with {proc.returncode}\n"
    except Exception as exc:  # pylint: disable=broad-except
        run["status"] = "error"
        run["output"] = f"Execution error: {exc}\n"


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route("/api/files/tree")
def api_tree():
    return ok(build_tree(WORKSPACE_ROOT))


@app.route("/api/files/read")
def api_read_file():
    try:
        req_path = request.args.get("path", "")
        path = safe_rel_path(req_path)
        return ok({"path": req_path, "content": path.read_text(encoding="utf-8")})
    except FileNotFoundError:
        return err("File not found", 404)
    except ValueError:
        return err("Invalid Python file path", 400)


@app.route("/api/files/save", methods=["POST"])
def api_save_file():
    payload = request.get_json(silent=True) or {}
    try:
        path = safe_rel_path(str(payload.get("path", "")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(payload.get("content", "")), encoding="utf-8")
        return ok({"saved": True})
    except ValueError:
        return err("Invalid Python file path", 400)


@app.route("/api/run", methods=["POST"])
def api_run_code():
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", ""))
    if not code.strip():
        return err("Python code is required")

    with run_lock:
        for existing in runs.values():
            if existing.get("status") == "running" and existing.get("process"):
                existing["process"].terminate()
                existing["status"] = "stopped"

        run_id = uuid.uuid4().hex
        runs[run_id] = {
            "id": run_id,
            "status": "running",
            "output": "",
            "created_at": time.time(),
            "process": None,
        }

        thread = threading.Thread(target=run_worker, args=(run_id, code), daemon=True)
        thread.start()

    return ok({"run_id": run_id})


@app.route("/api/run/<run_id>")
def api_run_status(run_id):
    run = runs.get(run_id)
    if not run:
        return err("Run not found", 404)
    return ok({"status": run["status"], "output": run["output"]})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    payload = request.get_json(silent=True) or {}
    run_id = payload.get("run_id")

    stopped = False
    with run_lock:
        targets = [runs.get(run_id)] if run_id and run_id in runs else list(runs.values())
        for run in targets:
            if not run:
                continue
            proc = run.get("process")
            if proc and run.get("status") == "running":
                proc.terminate()
                run["status"] = "stopped"
                run["output"] += "\nRun stopped by user.\n"
                stopped = True

    return ok({"stopped": stopped})


@app.route("/api/notebook")
def api_notebook():
    return ok(load_notebook())


@app.route("/api/notebook/category", methods=["POST"])
def api_add_category():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return err("Category name is required")

    data = load_notebook()
    if not any(cat["name"].lower() == name.lower() for cat in data["categories"]):
        data["categories"].append({"name": name, "notes": []})
        save_notebook(data)

    return ok(data)


@app.route("/api/notebook/note", methods=["POST"])
def api_add_note():
    payload = request.get_json(silent=True) or {}
    category = str(payload.get("category", "")).strip()
    title = str(payload.get("title", "Untitled note")).strip() or "Untitled note"
    code = str(payload.get("code", ""))

    if not category:
        return err("Category is required")

    data = load_notebook()
    target = next((cat for cat in data["categories"] if cat["name"].lower() == category.lower()), None)
    if target is None:
        target = {"name": category, "notes": []}
        data["categories"].append(target)

    target["notes"].append(
        {
            "id": uuid.uuid4().hex,
            "title": title,
            "code": code,
            "output": "",
            "language": "python",
        }
    )
    save_notebook(data)
    return ok(data)


@app.route("/api/notebook/save-output", methods=["POST"])
def api_save_note_output():
    payload = request.get_json(silent=True) or {}
    note_id = str(payload.get("note_id", ""))
    out = str(payload.get("output", ""))

    data = load_notebook()
    for category in data["categories"]:
        for note in category["notes"]:
            if note["id"] == note_id:
                note["output"] = out
                save_notebook(data)
                return ok(data)

    return err("Note not found", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
