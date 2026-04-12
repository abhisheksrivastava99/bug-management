import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "services" / "render_backend"))

MODULE_PATH = ROOT / "services" / "render_backend" / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("render_backend_main", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

from services.system1.app.main import LLM_CLIENT as SYSTEM1_LLM_CLIENT
from services.system3.app.main import LLM_CLIENT as SYSTEM3_LLM_CLIENT
from bug_management_shared.system4 import LLM_CLIENT as SYSTEM4_LLM_CLIENT


SYSTEM1_LLM_CLIENT.api_key = None
SYSTEM3_LLM_CLIENT.api_key = None
SYSTEM4_LLM_CLIENT.api_key = None
app = MODULE.app


class RenderBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_data_issue_returns_system4_and_four_steps(self) -> None:
        response = self.client.post("/chat/investigate", json={"raw_title": "TTY_TENTITY_Column UPDATEDDATE missing"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNotNone(payload["system3"])
        self.assertIsNotNone(payload["system4"])
        self.assertEqual([step["name"] for step in payload["steps"]], ["system1", "system2", "system3", "system4"])

    def test_infra_issue_skips_system4(self) -> None:
        response = self.client.post("/chat/investigate", json={"raw_title": "FIN_TORDER_cluster timeout in nightly run"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["system3"])
        self.assertIsNone(payload["system4"])
        self.assertEqual(payload["steps"][-1]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
