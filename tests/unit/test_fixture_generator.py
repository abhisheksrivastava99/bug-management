import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]


class FixtureGeneratorTests(unittest.TestCase):
    def test_generator_is_deterministic_and_consistent(self) -> None:
        env = dict(os.environ)
        env["BM_FIXTURE_SEED"] = "17"
        subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True, env=env)
        catalog_path = ROOT / "fixtures" / "catalog" / "scenario_catalog.json"
        first = json.loads(catalog_path.read_text(encoding="utf-8"))
        subprocess.run([sys.executable, "scripts/generate_excel_fixtures.py"], cwd=ROOT, check=True, env=env)
        second = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first["scenarios"]), 8)
        for scenario in first["scenarios"]:
            self.assertIn("root_cause_family", scenario)
            self.assertIn("mapping_rows", scenario)
            self.assertGreaterEqual(len(scenario["mapping_rows"]), 1)
            for row in scenario["mapping_rows"]:
                self.assertNotEqual(row["old_column_name"], row["new_column_name"])
                self.assertNotIn("mapping_status", row)

        workbook = load_workbook(ROOT / "fixtures" / "excel" / "column_mapping.xlsx", read_only=True)
        header = next(workbook.active.iter_rows(values_only=True))
        self.assertNotIn("mapping_status", header)
        self.assertEqual(
            header,
            (
                "old_system",
                "new_system",
                "old_table_name",
                "new_table_name",
                "old_column_name",
                "new_column_name",
                "data_type_old",
                "data_type_new",
            ),
        )


if __name__ == "__main__":
    unittest.main()
