from pathlib import Path
import os


class ProjectConfig:
    """Configuration for an ElectronicsMCP project."""

    def __init__(self, project_dir: str | Path | None = None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.data_dir = self.project_dir / "data"
        self.db_path = self.data_dir / "ee.db"
        self.output_dir = self.project_dir / "output"
        self.schematics_dir = self.output_dir / "schematics"
        self.plots_dir = self.output_dir / "plots"
        self.reports_dir = self.output_dir / "reports"
        self.netlists_dir = self.output_dir / "netlists"
        self.bom_dir = self.output_dir / "bom"
        self.models_dir = self.project_dir / "models"

    def ensure_dirs(self):
        """Create all project directories."""
        for d in [
            self.data_dir,
            self.schematics_dir,
            self.plots_dir,
            self.reports_dir,
            self.netlists_dir,
            self.bom_dir,
            self.models_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)
