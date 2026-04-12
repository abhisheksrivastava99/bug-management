import os
from pathlib import Path


def get_repo_root() -> Path:
    env_root = os.getenv("BM_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[4]


REPO_ROOT = get_repo_root()
FIXTURES_ROOT = REPO_ROOT / "fixtures"
EXCEL_ROOT = FIXTURES_ROOT / "excel"
SCRIPTS_ROOT = FIXTURES_ROOT / "scripts"
SQLITE_ROOT = FIXTURES_ROOT / "sqlite"
CATALOG_ROOT = FIXTURES_ROOT / "catalog"
