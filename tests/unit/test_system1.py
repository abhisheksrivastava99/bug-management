import importlib.util
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
MODULE_PATH = ROOT / "services" / "system1" / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("system1_main", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
app = MODULE.app


class System1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_parses_data_issue(self) -> None:
        response = self.client.post(
            "/parse-and-classify",
            json={"raw_title": "TTY_TENTITY_Column UPDATEDDATE missing"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["division"], "TTY")
        self.assertEqual(payload["table_name"], "TENTITY")
        self.assertEqual(payload["issue_classification"], "data_table_issue")
        self.assertIn("updateddate", payload["mentioned_columns"])

    def test_routes_infra_issue(self) -> None:
        response = self.client.post(
            "/parse-and-classify",
            json={"raw_title": "FIN_TORDER_cluster timeout in nightly run"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["routing_team"], "infra_team")

    def test_handles_spacing_variation(self) -> None:
        response = self.client.post(
            "/parse-and-classify",
            json={"raw_title": "tty  tcustomer  Column customer_status_code missing"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["table_name"], "TCUSTOMER")


if __name__ == "__main__":
    unittest.main()
