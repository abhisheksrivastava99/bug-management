import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True)
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))

from bug_management_shared.observability_models import ObservabilityFilters
from bug_management_shared.observability_service import ObservabilityService


class ObservabilityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ObservabilityService()
        self.service.llm_client.api_key = None

    def test_attention_profiles_match_seed_scenarios(self) -> None:
        response = self.service.get_pipelines(ObservabilityFilters())
        rows = {
            row.pipeline_name: row
            for group in response.groups
            for row in group.pipelines
        }
        self.assertEqual(rows["WeeklyRiskAggregation"].attention_reason, "Missed expected schedule")
        self.assertTrue(rows["WeeklyRiskAggregation"].stale)
        self.assertEqual(rows["DailyCustomerIngestion"].attention_reason, "Running slower than baseline")
        self.assertGreater(rows["DailyCustomerIngestion"].duration_delta_pct or 0, 0)
        self.assertTrue(rows["WeeklyInventorySnapshot"].recovered_after_failure)

    def test_detail_uses_pipeline_first_activity_rollup(self) -> None:
        detail = self.service.get_pipeline_detail("DailyFinanceReconciliation", ObservabilityFilters())
        self.assertGreaterEqual(len(detail.run_history), 1)
        self.assertGreaterEqual(len(detail.activity_summary), 1)
        self.assertGreaterEqual(detail.retry_summary.total_retries, 1)


if __name__ == "__main__":
    unittest.main()
