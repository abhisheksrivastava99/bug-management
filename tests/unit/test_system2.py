import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
MODULE_PATH = ROOT / "services" / "system2" / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("system2_main", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
app = MODULE.app


class System2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_resolves_mapping_when_issue_uses_gavin3_name(self) -> None:
        response = self.client.post(
            "/resolve-metadata",
            json={
                "division": "TTY",
                "table_name": "TENTITY",
                "issue": "Column UPDATEDDATE missing",
                "mentioned_columns": ["UPDATEDDATE"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["support_team"], "data_team_tty")
        self.assertEqual(payload["column_mapping"][0]["old_column_name"], "date_updated")
        self.assertEqual(payload["column_mapping"][0]["new_column_name"], "UPDATEDDATE")
        self.assertEqual(payload["column_mapping"][0]["mapping_status"], "renamed")
        self.assertGreater(len(payload["full_column_mapping"]), len(payload["column_mapping"]))
        self.assertTrue(
            any(row["new_column_name"] == "EntityIdentifier" for row in payload["full_column_mapping"])
        )

    def test_resolves_mapping_case_insensitively_for_gavin3_name(self) -> None:
        response = self.client.post(
            "/resolve-metadata",
            json={
                "division": "TTY",
                "table_name": "TENTITY",
                "issue": "Column updateddate missing",
                "mentioned_columns": ["updateddate"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["column_mapping"][0]["old_column_name"], "date_updated")
        self.assertEqual(payload["column_mapping"][0]["new_column_name"], "UPDATEDDATE")

    def test_resolves_mapping_when_issue_uses_legacy_name(self) -> None:
        response = self.client.post(
            "/resolve-metadata",
            json={
                "division": "TTY",
                "table_name": "TENTITY",
                "issue": "Column date_updated missing",
                "mentioned_columns": ["date_updated"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["column_mapping"][0]["old_column_name"], "date_updated")
        self.assertEqual(payload["column_mapping"][0]["new_column_name"], "UPDATEDDATE")

    def test_returns_not_found_for_unknown_table(self) -> None:
        response = self.client.post(
            "/resolve-metadata",
            json={
                "division": "TTY",
                "table_name": "UNKNOWN",
                "issue": "Column missing_business_field missing",
                "mentioned_columns": ["missing_business_field"],
            },
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
