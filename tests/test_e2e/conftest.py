"""E2E test fixtures: in-process uvicorn server sharing a Database with test code."""
import socket
import threading

import pytest
import uvicorn

from electronics_mcp.core.circuit_manager import CircuitManager
from electronics_mcp.core.database import Database
from electronics_mcp.core.schema import CircuitSchema
from electronics_mcp.web.app import app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def e2e_db(tmp_path_factory):
    """Session-scoped SQLite database for all e2e tests."""
    db_path = tmp_path_factory.mktemp("e2e") / "e2e.db"
    db = Database(db_path)
    db.initialize()
    return db


@pytest.fixture(scope="session")
def e2e_server(e2e_db):
    """Start uvicorn in a background thread, sharing e2e_db with the app."""
    app.state.db = e2e_db
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    import time
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture()
def circuit_manager(e2e_db) -> CircuitManager:
    """CircuitManager wired to the shared e2e database."""
    return CircuitManager(e2e_db)


@pytest.fixture()
def rc_circuit_id(circuit_manager) -> str:
    """Create an RC low-pass filter and return its circuit_id."""
    schema = CircuitSchema(
        name="RC Low-Pass",
        description="Simple RC low-pass filter",
        components=[
            {"id": "V1", "type": "voltage_source", "parameters": {"voltage": "5V"}, "nodes": ["in", "gnd"]},
            {"id": "R1", "type": "resistor", "parameters": {"resistance": "10k"}, "nodes": ["in", "out"]},
            {"id": "C1", "type": "capacitor", "parameters": {"capacitance": "100n"}, "nodes": ["out", "gnd"]},
        ],
    )
    return circuit_manager.create(schema)
