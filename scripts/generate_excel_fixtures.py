import json
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.fixture_catalog import build_scenario_catalog


EXCEL_DIR = REPO_ROOT / "fixtures" / "excel"
SCRIPTS_DIR = REPO_ROOT / "fixtures" / "scripts"
CATALOG_DIR = REPO_ROOT / "fixtures" / "catalog"
SQLITE_DIR = REPO_ROOT / "fixtures" / "sqlite"
MAPPING_COLUMNS = [
    "old_system",
    "new_system",
    "old_table_name",
    "new_table_name",
    "old_column_name",
    "new_column_name",
    "data_type_old",
    "data_type_new",
]


def main() -> None:
    seed = int(os.getenv("BM_FIXTURE_SEED", "11"))
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = build_scenario_catalog(seed=seed)

    metadata_rows = []
    mapping_rows = []
    for scenario in catalog["scenarios"]:
        division_dir = scenario["division"].lower()
        table_file = scenario["table_name"].lower() + ".py"
        old_path = SCRIPTS_DIR / "old" / division_dir / table_file
        new_path = SCRIPTS_DIR / "new" / division_dir / table_file
        old_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_text(scenario["old_script"], encoding="utf-8")
        new_path.write_text(scenario["new_script"], encoding="utf-8")

        metadata_rows.append(
            {
                "division": scenario["division"],
                "table_name": scenario["table_name"],
                "source_tables": ",".join(scenario["source_tables"]),
                "old_target_table_name": scenario["old_target_table_name"],
                "new_target_table_name": scenario["new_target_table_name"],
                "old_transformation_script_path": str(old_path.relative_to(REPO_ROOT)),
                "new_transformation_script_path": str(new_path.relative_to(REPO_ROOT)),
                "owner_users": ",".join(scenario["owner_users"]),
                "support_team": scenario["support_team"],
                "business_description": scenario["business_description"],
                "criticality": scenario["criticality"],
            }
        )

        for row in scenario["mapping_rows"]:
            mapping_rows.append(row)

        scenario["old_transformation_script_path"] = str(old_path.relative_to(REPO_ROOT))
        scenario["new_transformation_script_path"] = str(new_path.relative_to(REPO_ROOT))

    pd.DataFrame(metadata_rows).to_excel(EXCEL_DIR / "table_metadata.xlsx", index=False)
    pd.DataFrame(mapping_rows)[MAPPING_COLUMNS].to_excel(EXCEL_DIR / "column_mapping.xlsx", index=False)
    sqlite_path = _write_sqlite_fixture(catalog)
    (CATALOG_DIR / "scenario_catalog.json").write_text(
        json.dumps(catalog, indent=2),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(metadata_rows)} metadata rows, {len(mapping_rows)} mapping rows, "
        f"{len(catalog['scenarios'])} scenarios, and SQLite fixtures at {sqlite_path} using seed={seed}."
    )


def _write_sqlite_fixture(catalog: dict) -> Path:
    sqlite_path = SQLITE_DIR / "bug_management_demo.db"
    if sqlite_path.exists():
        sqlite_path.unlink()

    connection = sqlite3.connect(sqlite_path)
    try:
        for scenario in catalog["scenarios"]:
            sql_fixture = scenario["sql_fixture"]
            table_specs = [
                {
                    "name": scenario["new_target_table_name"],
                    "schema": sql_fixture["target_table_schema"],
                    "rows": sql_fixture["target_rows"],
                }
            ]
            table_specs.extend(sql_fixture.get("support_tables", []))
            for table_spec in table_specs:
                _create_table(connection, table_spec["name"], table_spec["schema"])
                _insert_rows(connection, table_spec["name"], table_spec.get("rows", []))
        connection.commit()
    finally:
        connection.close()
    return sqlite_path


def _create_table(connection: sqlite3.Connection, table_name: str, schema: list[dict]) -> None:
    columns_sql = ", ".join(f'"{column["name"]}" {column["type"]}' for column in schema)
    connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    connection.execute(f'CREATE TABLE "{table_name}" ({columns_sql})')


def _insert_rows(connection: sqlite3.Connection, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(f'"{column}"' for column in columns)
    values = [tuple(row.get(column) for column in columns) for row in rows]
    connection.executemany(
        f'INSERT INTO "{table_name}" ({column_sql}) VALUES ({placeholders})',
        values,
    )


if __name__ == "__main__":
    main()
