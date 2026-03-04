"""FastAPI web application for ElectronicsMCP browser UI."""
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from electronics_mcp.core.database import Database
from electronics_mcp.config import ProjectConfig


TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="ElectronicsMCP", docs_url="/api/docs")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register sub-routers
from electronics_mcp.web.stubs.parameter_explorer import router as explorer_router  # noqa: E402
app.include_router(explorer_router)


def _get_db(request: Request) -> Database:
    """Get database from app state or default."""
    if hasattr(request.app.state, "db"):
        return request.app.state.db
    config = ProjectConfig()
    return Database(config.db_path)


# --- Entity list views ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/circuits", response_class=HTMLResponse)
async def list_circuits(request: Request):
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, status, created_at "
            "FROM circuits ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    circuits = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "entity_list.html",
        {"request": request, "title": "Circuits", "items": circuits,
         "columns": ["name", "status", "created_at"],
         "detail_base": "/circuits"},
    )


@app.get("/circuits/{circuit_id}", response_class=HTMLResponse)
async def circuit_detail(request: Request, circuit_id: str):
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM circuits WHERE id = ?", (circuit_id,)
        ).fetchone()
    if not row:
        return HTMLResponse("Not found", status_code=404)
    item = dict(row)
    if item.get("schema_json"):
        try:
            item["schema_parsed"] = json.loads(item["schema_json"])
        except json.JSONDecodeError:
            pass
    return templates.TemplateResponse(
        "entity_detail.html",
        {"request": request, "title": item.get("name", "Circuit"),
         "item": item, "entity_type": "circuit"},
    )


@app.get("/components", response_class=HTMLResponse)
async def list_components(request: Request):
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, type, part_number, description "
            "FROM component_models ORDER BY type, part_number LIMIT 200"
        ).fetchall()
    items = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "entity_list.html",
        {"request": request, "title": "Components", "items": items,
         "columns": ["type", "part_number", "description"],
         "detail_base": "/components"},
    )


@app.get("/components/{component_id}", response_class=HTMLResponse)
async def component_detail(request: Request, component_id: str):
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM component_models WHERE id = ?", (component_id,)
        ).fetchone()
    if not row:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        "entity_detail.html",
        {"request": request, "title": dict(row).get("part_number", "Component"),
         "item": dict(row), "entity_type": "component"},
    )


@app.get("/knowledge", response_class=HTMLResponse)
async def list_knowledge(request: Request):
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, category, topic, title, difficulty "
            "FROM knowledge ORDER BY category, topic LIMIT 200"
        ).fetchall()
    items = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "entity_list.html",
        {"request": request, "title": "Knowledge Base", "items": items,
         "columns": ["category", "topic", "title", "difficulty"],
         "detail_base": "/knowledge"},
    )


@app.get("/knowledge/{knowledge_id}", response_class=HTMLResponse)
async def knowledge_detail(request: Request, knowledge_id: str):
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge WHERE id = ?", (knowledge_id,)
        ).fetchone()
    if not row:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        "entity_detail.html",
        {"request": request, "title": dict(row).get("title", "Knowledge"),
         "item": dict(row), "entity_type": "knowledge"},
    )


@app.get("/subcircuits", response_class=HTMLResponse)
async def list_subcircuits(request: Request):
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, category, description "
            "FROM subcircuits ORDER BY category, name LIMIT 200"
        ).fetchall()
    items = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "entity_list.html",
        {"request": request, "title": "Subcircuits", "items": items,
         "columns": ["name", "category", "description"],
         "detail_base": "/subcircuits"},
    )


@app.get("/subcircuits/{subcircuit_id}", response_class=HTMLResponse)
async def subcircuit_detail(request: Request, subcircuit_id: str):
    db = _get_db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM subcircuits WHERE id = ?", (subcircuit_id,)
        ).fetchone()
    if not row:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        "entity_detail.html",
        {"request": request, "title": dict(row).get("name", "Subcircuit"),
         "item": dict(row), "entity_type": "subcircuit"},
    )


# --- JSON API endpoints ---

@app.get("/api/circuits")
async def api_circuits(request: Request):
    db = _get_db(request)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, description, status FROM circuits"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/knowledge/search")
async def api_search_knowledge(request: Request, q: str = ""):
    db = _get_db(request)
    if not q:
        return []
    fts_query = " ".join(f'"{token}"' for token in q.split())
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT k.id, k.topic, k.title, k.category FROM knowledge k "
            "JOIN knowledge_fts fts ON k.rowid = fts.rowid "
            "WHERE knowledge_fts MATCH ? LIMIT 20",
            (fts_query,),
        ).fetchall()
    return [dict(r) for r in rows]
