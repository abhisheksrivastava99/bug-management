import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "services" / "system3"))
MODULE_PATH = ROOT / "services" / "system3" / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("system3_main", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
MODULE.LLM_CLIENT.api_key = None
app = MODULE.app


CATALOG = json.loads((ROOT / "fixtures" / "catalog" / "scenario_catalog.json").read_text(encoding="utf-8"))


def payloads_for_scenario(scenario_id: str):
    scenario = next(item for item in CATALOG["scenarios"] if item["id"] == scenario_id)
    system1 = {
        "raw_title": scenario["issue_title"],
        "division": scenario["division"],
        "table_name": scenario["table_name"],
        "issue": scenario["issue_title"].split("_", 2)[2],
        "mentioned_columns": scenario["focus_columns"],
        "issue_classification": "data_table_issue",
        "routing_team": "data_team",
        "confidence": 0.95,
        "parsing_notes": [],
    }
    system2 = {
        "division": scenario["division"],
        "table_name": scenario["table_name"],
        "old_target_table_name": scenario["old_target_table_name"],
        "new_target_table_name": scenario["new_target_table_name"],
        "source_tables": scenario["source_tables"],
        "old_transformation_script_path": scenario["old_transformation_script_path"],
        "new_transformation_script_path": scenario["new_transformation_script_path"],
        "owner_users": scenario["owner_users"],
        "support_team": scenario["support_team"],
        "business_description": scenario["business_description"],
        "criticality": scenario["criticality"],
        "column_mapping": scenario["mapping_rows"],
    }
    return system1, system2, scenario


class System3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_old_script_analysis_uses_legacy_name_from_mapping(self) -> None:
        system1, system2, _ = payloads_for_scenario("tty_tentity_missing_final_select")
        response = self.client.post(
            "/analyze-old-script",
            json={"system1": system1, "system2": system2, "script_role": "old"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["prompt_version"], "system3.v4")
        self.assertIn("date_updated", payload["relevant_columns"])
        self.assertNotIn("UPDATEDDATE", payload["relevant_columns"])

    def test_missing_final_select_regression(self) -> None:
        system1, system2, _ = payloads_for_scenario("tty_tentity_missing_final_select")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["root_cause_family"], "missing_final_select")
        self.assertEqual(payload["decision"], "regression_detected")
        self.assertIn("date_updated -> UPDATEDDATE", payload["likely_root_cause"])

    def test_alias_mismatch_case(self) -> None:
        system1, system2, _ = payloads_for_scenario("tty_tcustomer_wrong_new_alias")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["root_cause_family"], "alias_mismatch")
        self.assertEqual(payload["decision"], "regression_detected")

    def test_renamed_derivation_case(self) -> None:
        system1, system2, _ = payloads_for_scenario("fin_tinvoice_renamed_derivation")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["root_cause_family"], "renamed_derivation")
        self.assertEqual(payload["decision"], "regression_detected")

    def test_filter_row_loss_case(self) -> None:
        system1, system2, _ = payloads_for_scenario("ops_tinventory_filter_row_loss")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["root_cause_family"], "filter_row_loss")
        self.assertIn("filter", payload["likely_root_cause"].lower())

    def test_source_column_disappearance_case(self) -> None:
        system1, system2, _ = payloads_for_scenario("tty_tprofile_source_column_disappearance")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "upstream_source_check_required")
        self.assertEqual(payload["root_cause_family"], "source_column_disappearance")

    def test_insufficient_evidence_case(self) -> None:
        system1, system2, _ = payloads_for_scenario("ops_tbalance_insufficient_evidence")
        response = self.client.post("/analyze-incident", json={"system1": system1, "system2": system2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "insufficient_evidence")
        self.assertGreaterEqual(len(payload["evidence_gaps"]), 1)


if __name__ == "__main__":
    unittest.main()
