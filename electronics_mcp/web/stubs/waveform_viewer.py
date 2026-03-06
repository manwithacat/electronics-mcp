"""Waveform viewer: interactive Plotly.js-based time/frequency plots."""
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from electronics_mcp.core.database import Database

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

router = APIRouter(prefix="/waveforms", tags=["waveforms"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_db(request: Request) -> Database:
    if hasattr(request.app.state, "db"):
        return request.app.state.db
    from electronics_mcp.config import ProjectConfig
    return Database(ProjectConfig().db_path)


@router.get("/{circuit_id}", response_class=HTMLResponse)
async def waveform_view(request: Request, circuit_id: str):
    """Render waveform viewer for a circuit's simulation results."""
    db = _get_db(request)
    with db.connect() as conn:
        circuit = conn.execute(
            "SELECT id, name FROM circuits WHERE id = ?", (circuit_id,)
        ).fetchone()
        if not circuit:
            return HTMLResponse("Circuit not found", status_code=404)

        sims = conn.execute(
            "SELECT id, analysis_type, results_json, parameters, created_at "
            "FROM simulation_results WHERE circuit_id = ? "
            "ORDER BY created_at DESC LIMIT 20",
            (circuit_id,),
        ).fetchall()

    sim_data = []
    for sim in sims:
        try:
            results = json.loads(sim["results_json"])
        except (json.JSONDecodeError, TypeError):
            results = {}
        sim_data.append({
            "id": sim["id"],
            "analysis_type": sim["analysis_type"],
            "results": results,
            "parameters": sim["parameters"],
            "created_at": sim["created_at"],
        })

    return templates.TemplateResponse(
        "waveform_viewer.html",
        {"request": request, "circuit": dict(circuit),
         "simulations": sim_data},
    )


@router.get("/{circuit_id}/data/{sim_id}")
async def waveform_data(request: Request, circuit_id: str, sim_id: str):
    """Return simulation data as JSON for Plotly rendering."""
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT results_json, analysis_type FROM simulation_results "
            "WHERE id = ? AND circuit_id = ?",
            (sim_id, circuit_id),
        ).fetchone()
    if not row:
        return {"error": "Simulation not found"}
    try:
        results = json.loads(row["results_json"])
    except (json.JSONDecodeError, TypeError):
        results = {}

    # Normalize keys for frontend JS expectations
    analysis_type = row["analysis_type"]
    if analysis_type == "transient":
        # Ensure {time, signals: {name: [values]}} structure
        if "time" in results and "voltage" in results and "signals" not in results:
            results["signals"] = {"voltage": results.pop("voltage")}
        elif "time" in results and "signals" not in results:
            # Collect any non-time numeric arrays as signals
            signals = {}
            for k, v in list(results.items()):
                if k != "time" and isinstance(v, list):
                    signals[k] = v
            if signals:
                for k in signals:
                    results.pop(k, None)
                results["signals"] = signals
    elif analysis_type == "ac":
        # Ensure magnitude key (not magnitude_db)
        if "magnitude_db" in results and "magnitude" not in results:
            results["magnitude"] = results.pop("magnitude_db")

    return {"analysis_type": analysis_type, "data": results}
