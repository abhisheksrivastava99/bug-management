import asyncio
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

SYSTEM3_MODULE_PATH = ROOT / "services" / "system3" / "app" / "main.py"
SYSTEM3_SPEC = importlib.util.spec_from_file_location("system3_for_system4", SYSTEM3_MODULE_PATH)
SYSTEM3_MODULE = importlib.util.module_from_spec(SYSTEM3_SPEC)
assert SYSTEM3_SPEC and SYSTEM3_SPEC.loader
SYSTEM3_SPEC.loader.exec_module(SYSTEM3_MODULE)
SYSTEM3_MODULE.LLM_CLIENT.api_key = None
SYSTEM3_APP = SYSTEM3_MODULE.app

from bug_management_shared.models import System4Request
from bug_management_shared.system4 import LLM_CLIENT as SYSTEM4_LLM_CLIENT
from bug_management_shared.system4 import analyze_system4


SYSTEM4_LLM_CLIENT.api_key = None
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
        "full_column_mapping": scenario["mapping_rows"],
    }
    return system1, system2, scenario


def analyze_new_script_payload(client: TestClient, system1: dict, system2: dict) -> dict:
    response = client.post(
        "/analyze-new-script",
        json={"system1": system1, "system2": system2, "script_role": "new"},
    )
    if response.status_code != 200:
        raise AssertionError(f"new-script analysis failed: {response.status_code} {response.text}")
    return response.json()


class System4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.system3_client = TestClient(SYSTEM3_APP)

    def _run_system4(self, scenario_id: str):
        system1, system2, _ = payloads_for_scenario(scenario_id)
        new_analysis = analyze_new_script_payload(self.system3_client, system1, system2)
        return asyncio.run(
            analyze_system4(
                System4Request(
                    system1=system1,
                    system2=system2,
                    new_analysis=new_analysis,
                )
            )
        )

    def test_missing_final_select_returns_sql_findings(self) -> None:
        result = self._run_system4("tty_tentity_missing_final_select")
        self.assertEqual(result.scenario_type, "missing_final_select")
        self.assertTrue(any("UPDATEDDATE" in finding for finding in result.issue_findings))
        self.assertGreaterEqual(result.primary_query.row_count, 1)

    def test_duplicate_data_returns_duplicate_diagnostics(self) -> None:
        result = self._run_system4("ops_tdupshipment_duplicate_rows")
        self.assertEqual(result.scenario_type, "duplicate_data")
        self.assertTrue(any("Duplicate" in finding for finding in result.issue_findings))
        diagnostic_names = {item.name for item in result.diagnostic_queries}
        self.assertIn("Duplicate key counts", diagnostic_names)

    def test_invalid_type_format_finds_bad_timestamp_strings(self) -> None:
        result = self._run_system4("tty_teventlog_invalid_date_format")
        self.assertEqual(result.scenario_type, "invalid_type_format")
        self.assertTrue(any("timestamp" in finding.lower() for finding in result.issue_findings))

    def test_join_null_spike_finds_join_side_evidence(self) -> None:
        result = self._run_system4("fin_torder_join_null_spike")
        self.assertEqual(result.scenario_type, "join_null_spike")
        self.assertTrue(any("join" in finding.lower() for finding in result.issue_findings))

    def test_filter_row_loss_finds_filter_loss(self) -> None:
        result = self._run_system4("ops_tinventory_filter_row_loss")
        self.assertEqual(result.scenario_type, "filter_row_loss")
        self.assertTrue(any("filter" in finding.lower() for finding in result.issue_findings))

    def test_join_filter_miss_finds_eligibility_filter_issue(self) -> None:
        result = self._run_system4("fin_torderlink_join_filter_miss")
        self.assertEqual(result.scenario_type, "join_filter_miss")
        self.assertTrue(any("eligibility" in finding.lower() or "filter" in finding.lower() for finding in result.issue_findings))

    def test_unmatched_issue_returns_warning_only_payload(self) -> None:
        system1 = {
            "raw_title": "TTY_UNKNOWN_Column made_up_field missing",
            "division": "TTY",
            "table_name": "UNKNOWN",
            "issue": "Column made_up_field missing",
            "mentioned_columns": ["made_up_field"],
            "issue_classification": "data_table_issue",
            "routing_team": "data_team",
            "confidence": 0.9,
            "parsing_notes": [],
        }
        system2 = {
            "division": "TTY",
            "table_name": "UNKNOWN",
            "old_target_table_name": "unknown_old",
            "new_target_table_name": "unknown_new",
            "source_tables": [],
            "old_transformation_script_path": "",
            "new_transformation_script_path": "",
            "owner_users": [],
            "support_team": "data_team_tty",
            "business_description": "Unknown table",
            "criticality": "low",
            "column_mapping": [],
            "full_column_mapping": [],
        }
        new_analysis = {
            "script_role": "new",
            "script_path": "",
            "issue_focus": "Column made_up_field missing",
            "summary": "No analysis available.",
            "prompt_version": "system3.v4",
            "decision": "insufficient_evidence",
            "relevant_columns": [],
            "observations": [],
            "suspected_causes": [],
            "evidence": [],
            "evidence_gaps": [],
            "unresolved_questions": [],
            "analysis_warnings": [],
            "confidence": 0.1,
        }
        result = asyncio.run(
            analyze_system4(
                System4Request(
                    system1=system1,
                    system2=system2,
                    new_analysis=new_analysis,
                )
            )
        )
        self.assertEqual(result.primary_query.row_count, 0)
        self.assertGreaterEqual(len(result.warnings), 1)


if __name__ == "__main__":
    unittest.main()
