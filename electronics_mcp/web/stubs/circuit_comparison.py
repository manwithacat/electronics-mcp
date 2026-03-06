"""Circuit comparison: side-by-side display with overlaid plots and metrics."""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from electronics_mcp.core.database import Database

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

router = APIRouter(prefix="/compare", tags=["comparison"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_db(request: Request) -> Database:
    if hasattr(request.app.state, "db"):
        return request.app.state.db
    from electronics_mcp.config import ProjectConfig

    return Database(ProjectConfig().db_path)


@router.get("/", response_class=HTMLResponse)
async def comparison_list(request: Request):
    """List saved comparisons."""
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, circuit_ids, created_at "
            "FROM comparisons ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    items = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "circuit_comparison.html",
        {"request": request, "comparisons": items, "detail": None},
    )


@router.get("/{comparison_id}", response_class=HTMLResponse)
async def comparison_detail(request: Request, comparison_id: str):
    """Show comparison detail with circuit data side-by-side."""
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM comparisons WHERE id = ?", (comparison_id,)
        ).fetchone()
        if not row:
            return HTMLResponse("Comparison not found", status_code=404)

        comp = dict(row)
        circuit_ids = json.loads(comp.get("circuit_ids", "[]"))
        circuits = []
        for cid in circuit_ids:
            circuit = conn.execute(
                "SELECT id, name, description, schema_json FROM circuits WHERE id = ?",
                (cid,),
            ).fetchone()
            if circuit:
                circuits.append(dict(circuit))

        axes = []
        if comp.get("comparison_axes"):
            try:
                axes = json.loads(comp["comparison_axes"])
            except json.JSONDecodeError:
                pass

        results = {}
        if comp.get("results"):
            try:
                results = json.loads(comp["results"])
            except json.JSONDecodeError:
                pass

    return templates.TemplateResponse(
        "circuit_comparison.html",
        {
            "request": request,
            "comparisons": [],
            "detail": comp,
            "circuits": circuits,
            "axes": axes,
            "results": results,
        },
    )


@router.get("/{comparison_id}/data")
async def comparison_data(request: Request, comparison_id: str):
    """Return comparison data as JSON for overlay plots."""
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT circuit_ids, comparison_axes, results "
            "FROM comparisons WHERE id = ?",
            (comparison_id,),
        ).fetchone()
    if not row:
        return {"error": "Comparison not found"}
    return {
        "circuit_ids": json.loads(row["circuit_ids"] or "[]"),
        "axes": json.loads(row["comparison_axes"] or "[]"),
        "results": json.loads(row["results"] or "{}"),
    }


@router.post("/{comparison_id}/run")
async def comparison_run(request: Request, comparison_id: str):
    """Run AC analysis on all circuits in comparison and build overlay data."""
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT circuit_ids FROM comparisons WHERE id = ?", (comparison_id,)
        ).fetchone()
        if not row:
            return JSONResponse({"error": "Comparison not found"}, status_code=404)

        circuit_ids = json.loads(row["circuit_ids"] or "[]")
        overlay = {"circuits": {}}

        for cid in circuit_ids:
            # Get latest AC sim results for this circuit
            sim = conn.execute(
                "SELECT results_json FROM simulation_results "
                "WHERE circuit_id = ? AND analysis_type = 'ac' "
                "ORDER BY rowid DESC LIMIT 1",
                (cid,),
            ).fetchone()

            circuit = conn.execute(
                "SELECT name FROM circuits WHERE id = ?", (cid,)
            ).fetchone()
            name = circuit["name"] if circuit else cid

            if sim:
                results = json.loads(sim["results_json"])
                overlay["circuits"][cid] = {
                    "name": name,
                    "frequency": results.get("frequency", []),
                    "magnitude": results.get(
                        "magnitude_db", results.get("magnitude", [])
                    ),
                    "phase": results.get("phase_deg", results.get("phase", [])),
                }
            else:
                overlay["circuits"][cid] = {"name": name, "error": "No AC results"}

        # Save results back to comparison
        conn.execute(
            "UPDATE comparisons SET results = ? WHERE id = ?",
            (json.dumps(overlay), comparison_id),
        )

    return overlay
