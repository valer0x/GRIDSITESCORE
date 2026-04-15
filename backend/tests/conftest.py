import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "SCORING_CONFIG_PATH", str(BACKEND_ROOT / "scoring_config.yaml")
)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://idd:idd@localhost:5432/idd_test"
)


@pytest.fixture(scope="session")
def scoring_config_path() -> str:
    return os.environ["SCORING_CONFIG_PATH"]
