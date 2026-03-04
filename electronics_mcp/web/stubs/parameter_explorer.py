"""Parameter explorer: interactive circuit parameter adjustment with live simulation."""
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from electronics_mcp.core.database import Database

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

router = APIRouter(prefix="/explorer", tags=["explorer"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_db(request: Request) -> Database:
    if hasattr(request.app.state, "db"):
        return request.app.state.db
    from electronics_mcp.config import ProjectConfig
    config = ProjectConfig()
    return Database(config.db_path)


@router.get("/{circuit_id}", response_class=HTMLResponse)
async def explorer_view(request: Request, circuit_id: str):
    """Render parameter explorer for a circuit."""
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, name, schema_json FROM circuits WHERE id = ?",
            (circuit_id,),
        ).fetchone()
    if not row:
        return HTMLResponse("Circuit not found", status_code=404)

    circuit = dict(row)
    schema = json.loads(circuit["schema_json"])
    components = schema.get("components", [])

    # Extract adjustable parameters
    params = []
    for comp in components:
        comp_params = comp.get("parameters", {})
        for pname, pvalue in comp_params.items():
            params.append({
                "component_id": comp.get("id", ""),
                "component_type": comp.get("type", ""),
                "param_name": pname,
                "current_value": str(pvalue),
            })

    return templates.TemplateResponse(
        "parameter_explorer.html",
        {"request": request, "circuit": circuit, "params": params},
    )


@router.post("/{circuit_id}/simulate", response_class=HTMLResponse)
async def simulate_with_params(request: Request, circuit_id: str):
    """Re-simulate circuit with updated parameters (HTMX endpoint)."""
    db = _get_db(request)
    form = await request.form()

    with db.connect() as conn:
        row = conn.execute(
            "SELECT schema_json FROM circuits WHERE id = ?",
            (circuit_id,),
        ).fetchone()
    if not row:
        return HTMLResponse("Circuit not found", status_code=404)

    schema = json.loads(row["schema_json"])
    components = schema.get("components", [])

    # Apply parameter updates from form
    for comp in components:
        comp_id = comp.get("id", "")
        comp_params = comp.get("parameters", {})
        for pname in list(comp_params.keys()):
            form_key = f"{comp_id}__{pname}"
            if form_key in form:
                comp_params[pname] = form[form_key]

    # Return updated parameter summary as HTML fragment
    lines = []
    for comp in components:
        comp_id = comp.get("id", "")
        for pname, pval in comp.get("parameters", {}).items():
            lines.append(f"<li><strong>{comp_id}.{pname}</strong>: {pval}</li>")

    return HTMLResponse(
        f'<div class="card"><h3>Updated Parameters</h3>'
        f'<ul>{"".join(lines)}</ul>'
        f'<p>Simulation results would appear here with a running SPICE engine.</p>'
        f'</div>'
    )
