import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "services" / "system3"))

MODULE_PATH = ROOT / "services" / "system3" / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("system3_eval_main", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
APP = MODULE.app


def _load_catalog():
    path = ROOT / "fixtures" / "catalog" / "scenario_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_payload(scenario):
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
    return {"system1": system1, "system2": system2}


def run(mode: str) -> int:
    if mode == "live" and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for --mode live")
    if mode == "mocked":
        MODULE.LLM_CLIENT.api_key = None

    catalog = _load_catalog()
    client = TestClient(APP)
    results = []
    for scenario in catalog["scenarios"]:
        if not scenario["golden"]:
            continue
        response = client.post("/analyze-incident", json=_scenario_payload(scenario))
        if response.status_code != 200:
            raise AssertionError(f"{scenario['id']} failed: {response.status_code} {response.text}")
        payload = response.json()
        results.append(
            {
                "scenario_id": scenario["id"],
                "expected_root_cause_family": scenario["root_cause_family"],
                "actual_root_cause_family": payload.get("root_cause_family"),
                "expected_decision": scenario["decision"],
                "actual_decision": payload.get("decision"),
                "matched_root_cause_family": scenario["root_cause_family"] == payload.get("root_cause_family"),
                "matched_decision": scenario["decision"] == payload.get("decision"),
                "keyword_hits": [
                    keyword
                    for keyword in scenario.get("expected_keywords", [])
                    if keyword.lower() in json.dumps(payload).lower()
                ],
                "final_summary": payload.get("final_summary"),
            }
        )

    total = len(results)
    matches = sum(1 for item in results if item["matched_root_cause_family"] and item["matched_decision"])
    print(json.dumps({"mode": mode, "matched": matches, "total": total, "results": results}, indent=2))
    return 0 if matches == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mocked", "live"], default="mocked")
    args = parser.parse_args()
    return run(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
