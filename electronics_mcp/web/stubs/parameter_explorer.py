"""Parameter explorer: interactive circuit parameter adjustment with live simulation."""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import (
    CircuitModification,
    CircuitSchema,
    ComponentUpdate,
)
from electronics_mcp.engines.simulation.numerical import NumericalSimulator

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
            params.append(
                {
                    "component_id": comp.get("id", ""),
                    "component_type": comp.get("type", ""),
                    "param_name": pname,
                    "current_value": str(pvalue),
                }
            )

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

    analysis_type = form.get("analysis_type", "dc_op")

    # Run real simulation
    try:
        schema_obj = CircuitSchema.model_validate(schema)
        sim = NumericalSimulator()

        if analysis_type == "ac":
            result = sim.ac_analysis(schema_obj)
        elif analysis_type == "transient":
            result = sim.transient_analysis(schema_obj)
        else:
            result = sim.dc_operating_point(schema_obj)

        # Save result to DB
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO simulation_results (id, circuit_id, analysis_type, parameters, results_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    circuit_id,
                    analysis_type,
                    json.dumps({"source": "parameter_explorer"}),
                    json.dumps(result),
                ),
            )

        # Build HTML response with real results
        lines = ['<div class="card"><h3>Simulation Results</h3>']
        lines.append(f"<p><strong>Analysis:</strong> {analysis_type}</p>")

        if analysis_type == "dc_op" and "node_voltages" in result:
            lines.append("<h4>Node Voltages</h4><ul>")
            for node, voltage in result["node_voltages"].items():
                lines.append(f"<li><strong>{node}</strong>: {voltage:.4g} V</li>")
            lines.append("</ul>")
            if "branch_currents" in result:
                lines.append("<h4>Branch Currents</h4><ul>")
                for branch, current in result["branch_currents"].items():
                    lines.append(f"<li><strong>{branch}</strong>: {current:.4g} A</li>")
                lines.append("</ul>")
        elif analysis_type == "ac":
            if "bandwidth_hz" in result:
                lines.append(
                    f"<p><strong>Bandwidth:</strong> {result['bandwidth_hz']:.2f} Hz</p>"
                )
            if "dc_gain_db" in result:
                lines.append(
                    f"<p><strong>DC Gain:</strong> {result['dc_gain_db']:.2f} dB</p>"
                )
        elif analysis_type == "transient":
            if "rise_time" in result:
                lines.append(
                    f"<p><strong>Rise Time:</strong> {result['rise_time']:.4g} s</p>"
                )
            if "overshoot_pct" in result:
                lines.append(
                    f"<p><strong>Overshoot:</strong> {result['overshoot_pct']:.1f}%</p>"
                )

        # Show updated parameters
        lines.append("<h4>Parameters Used</h4><ul>")
        for comp in components:
            comp_id = comp.get("id", "")
            for pname, pval in comp.get("parameters", {}).items():
                lines.append(f"<li><strong>{comp_id}.{pname}</strong>: {pval}</li>")
        lines.append("</ul></div>")
        return HTMLResponse("".join(lines))

    except Exception as e:
        return HTMLResponse(
            f'<div class="card"><h3>Simulation Error</h3>'
            f'<p style="color:red;">{type(e).__name__}: {e}</p>'
            f"</div>"
        )


@router.post("/{circuit_id}/save", response_class=HTMLResponse)
async def save_parameters(request: Request, circuit_id: str):
    """Persist modified parameters back to the circuit in the database."""
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

    # Detect which parameters changed
    updates = []
    for comp in components:
        comp_id = comp.get("id", "")
        comp_params = comp.get("parameters", {})
        changed_params = {}
        for pname, pvalue in comp_params.items():
            form_key = f"{comp_id}__{pname}"
            if form_key in form:
                form_val = form[form_key]
                if str(form_val) != str(pvalue):
                    changed_params[pname] = str(form_val)
        if changed_params:
            updates.append(ComponentUpdate(id=comp_id, parameters=changed_params))

    if not updates:
        return HTMLResponse(
            '<div class="card" style="color:#666;">'
            "<p>No parameter changes to save.</p></div>"
        )

    mod = CircuitModification(update=updates)
    mgr = CircuitManager(db)
    new_version = mgr.modify(circuit_id, mod)

    return HTMLResponse(
        '<div class="card" style="color:green;">'
        f"<p>Parameters saved. Version: {new_version}</p></div>"
    )
