import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "services" / "system3"))

PROMPT_MODULE_PATH = ROOT / "services" / "system3" / "app" / "prompt_pack.py"
MODELS_MODULE_PATH = ROOT / "packages" / "shared" / "src" / "bug_management_shared" / "models.py"

prompt_spec = importlib.util.spec_from_file_location("system3_prompt_pack", PROMPT_MODULE_PATH)
prompt_module = importlib.util.module_from_spec(prompt_spec)
assert prompt_spec and prompt_spec.loader
prompt_spec.loader.exec_module(prompt_module)

models_spec = importlib.util.spec_from_file_location("shared_models", MODELS_MODULE_PATH)
models_module = importlib.util.module_from_spec(models_spec)
assert models_spec and models_spec.loader
models_spec.loader.exec_module(models_module)


def build_payloads():
    system1 = models_module.System1Result(
        raw_title="TTY_TENTITY_Column UPDATEDDATE missing",
        division="TTY",
        table_name="TENTITY",
        issue="Column UPDATEDDATE missing",
        mentioned_columns=["updateddate"],
        issue_classification="data_table_issue",
        routing_team="data_team",
        confidence=0.95,
        parsing_notes=[],
    )
    system2 = models_module.ResolvedMetadata(
        division="TTY",
        table_name="TENTITY",
        old_target_table_name="tentity_old",
        new_target_table_name="tentity_new",
        source_tables=["src_tentity_base", "src_tentity_audit"],
        old_transformation_script_path=str(ROOT / "fixtures" / "scripts" / "old" / "tty" / "tentity.py"),
        new_transformation_script_path=str(ROOT / "fixtures" / "scripts" / "new" / "tty" / "tentity.py"),
        owner_users=["tty_owner"],
        support_team="data_team_tty",
        business_description="Core entity master data for the TTY division.",
        criticality="high",
        column_mapping=[
            models_module.ColumnMappingRecord(
                old_system="Gavin2",
                new_system="Gavin3",
                old_table_name="tentity_old",
                new_table_name="tentity_new",
                old_column_name="date_updated",
                new_column_name="UPDATEDDATE",
                data_type_old="timestamp",
                data_type_new="timestamp",
            )
        ],
    )
    analysis = models_module.ScriptAnalysis(
        script_role="old",
        script_path=str(ROOT / "fixtures" / "scripts" / "old" / "tty" / "tentity.py"),
        issue_focus="Column UPDATEDDATE missing",
        summary="Old script keeps date_updated in the final select.",
        prompt_version="system3.v4",
        decision="supported",
        relevant_columns=["date_updated"],
        observations=["Column date_updated appears in a select statement."],
        suspected_causes=[],
        evidence=[],
        evidence_gaps=[],
        unresolved_questions=[],
        analysis_warnings=[],
        confidence=0.9,
    )
    script_request = models_module.ScriptAnalysisRequest(system1=system1, system2=system2, script_role="old")
    compare_request = models_module.CompareAnalysesRequest(
        system1=system1,
        system2=system2,
        old_analysis=analysis,
        new_analysis=analysis.model_copy(update={"script_role": "new", "decision": "partially_supported"}),
    )
    return script_request, analysis, compare_request


class PromptPackTests(unittest.TestCase):
    def test_script_prompt_contains_mapping_bridge_language(self) -> None:
        request, analysis, _ = build_payloads()
        prompt = prompt_module.build_script_analysis_prompt(request, analysis)
        text = prompt["user_prompt"]
        self.assertIn("## Incident Context", text)
        self.assertIn("## Resolved Metadata", text)
        self.assertIn("## Focused Evidence", text)
        self.assertIn("evidence_gaps", text)
        self.assertIn("canonical translation layer", text)
        self.assertIn("Literal name equality across old and new scripts is not expected", prompt["system_prompt"])

    def test_synthesis_prompt_uses_analysis_outputs_and_allowed_families(self) -> None:
        _, _, compare_request = build_payloads()
        prompt = prompt_module.build_synthesis_prompt(compare_request)
        text = prompt["user_prompt"]
        self.assertIn("## Old Analysis Summary", text)
        self.assertIn("## New Analysis Summary", text)
        self.assertIn("## Allowed Root Cause Families", text)
        self.assertIn("date_updated -> UPDATEDDATE", text)
        self.assertNotIn("def transform", text)


if __name__ == "__main__":
    unittest.main()
