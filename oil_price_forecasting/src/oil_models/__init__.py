"""Oil price forecasting models: Kilian SVAR, Hormuz disruption scenarios,
supply-demand regressions, forecast combination, and evaluation."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
DATA_RAW = PROJECT_DIR / "data" / "raw"
DATA_PROCESSED = PROJECT_DIR / "data" / "processed"
DATA_EXTERNAL = PROJECT_DIR / "data" / "external"
REPORTS_DIR = PROJECT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
