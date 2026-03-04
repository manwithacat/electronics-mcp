import pytest
from pathlib import Path
from electronics_mcp.config import ProjectConfig


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with config."""
    config = ProjectConfig(tmp_path)
    config.ensure_dirs()
    return config
