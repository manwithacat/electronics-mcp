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
    return {"analysis_type": row["analysis_type"], "data": results}
