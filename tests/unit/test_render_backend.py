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
from bug_management_shared.observability_router import OBSERVABILITY_SERVICE


SYSTEM1_LLM_CLIENT.api_key = None
SYSTEM3_LLM_CLIENT.api_key = None
SYSTEM4_LLM_CLIENT.api_key = None
OBSERVABILITY_SERVICE.llm_client.api_key = None
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

    def test_observability_summary_and_groups_load(self) -> None:
        summary_response = self.client.get("/observability/summary")
        pipelines_response = self.client.get("/observability/pipelines")
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(pipelines_response.status_code, 200)
        summary_payload = summary_response.json()
        pipelines_payload = pipelines_response.json()
        self.assertEqual(len(summary_payload["summary_metrics"]), 5)
        self.assertEqual([group["total_count"] for group in pipelines_payload["groups"]], [3, 3, 2])
        self.assertGreaterEqual(len(summary_payload["attention_items"]), 1)

    def test_observability_detail_and_query_fallback(self) -> None:
        detail_response = self.client.get("/observability/pipelines/DailyFinanceReconciliation")
        summary_payload = self.client.get("/observability/summary").json()
        groups_payload = self.client.get("/observability/pipelines").json()["groups"]
        summary_ai_response = self.client.post(
            "/observability/summary-ai",
            json={
                "summary": summary_payload,
                "groups": groups_payload,
            },
        )
        query_response = self.client.post(
            "/observability/query",
            json={
                "question": "Which weekly pipelines are getting slower?",
                "filters": {"window_days": 30},
            },
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(summary_ai_response.status_code, 200)
        self.assertEqual(query_response.status_code, 200)
        detail_payload = detail_response.json()
        summary_ai_payload = summary_ai_response.json()
        query_payload = query_response.json()
        self.assertGreaterEqual(len(detail_payload["run_history"]), 1)
        self.assertGreaterEqual(len(detail_payload["activity_summary"]), 1)
        self.assertIn("summary", summary_ai_payload)
        self.assertTrue(summary_ai_payload["used_fallback"])
        self.assertIn("ADFPipelineRun", query_payload["display_kql"])
        self.assertTrue(query_payload["used_fallback"])


if __name__ == "__main__":
    unittest.main()
