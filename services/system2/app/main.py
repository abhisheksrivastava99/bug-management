import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.config import EXCEL_ROOT
from bug_management_shared.logging_utils import configure_logging
from bug_management_shared.models import ColumnMappingRecord, ResolvedMetadata, System2Request
from bug_management_shared.text_utils import dedupe, normalize_key


configure_logging("system2")
LOGGER = logging.getLogger("system2")
app = FastAPI(title="System 2 - Metadata Resolver", version="0.1.0")

METADATA_PATH = Path(os.getenv("BM_METADATA_XLSX", EXCEL_ROOT / "table_metadata.xlsx"))
MAPPING_PATH = Path(os.getenv("BM_MAPPING_XLSX", EXCEL_ROOT / "column_mapping.xlsx"))
STATE: Dict[str, Any] = {"metadata_df": None, "mapping_df": None, "ready": False}


@app.on_event("startup")
def startup() -> None:
    _load_excels()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "system2"}


@app.get("/ready")
async def ready() -> dict:
    return {
        "status": "ready" if STATE["ready"] else "not_ready",
        "service": "system2",
        "metadata_path": str(METADATA_PATH),
        "mapping_path": str(MAPPING_PATH),
    }


@app.post("/resolve-metadata", response_model=ResolvedMetadata)
async def resolve_metadata(payload: System2Request) -> ResolvedMetadata:
    if not STATE["ready"]:
        _load_excels()
    metadata_df = STATE["metadata_df"]
    mapping_df = STATE["mapping_df"]
    division_key = normalize_key(payload.division)
    table_key = normalize_key(payload.table_name)

    row_df = metadata_df[
        (metadata_df["division_key"] == division_key)
        & (metadata_df["table_key"] == table_key)
    ]
    if row_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"no metadata found for division={payload.division} table={payload.table_name}",
        )
    row = row_df.iloc[0]
    old_table = row["old_target_table_name"]
    new_table = row["new_target_table_name"]

    relevant_rows = mapping_df[
        (mapping_df["old_table_key"] == normalize_key(old_table))
        | (mapping_df["new_table_key"] == normalize_key(new_table))
    ]
    mentioned = [normalize_key(item) for item in payload.mentioned_columns]
    focused_rows = relevant_rows
    if mentioned:
        filtered = relevant_rows[
            relevant_rows["old_column_key"].isin(mentioned)
            | relevant_rows["new_column_key"].isin(mentioned)
        ]
        if not filtered.empty:
            focused_rows = filtered

    column_mapping = _serialize_mapping_rows(focused_rows)
    full_column_mapping = _serialize_mapping_rows(relevant_rows)

    return ResolvedMetadata(
        division=row["division"],
        table_name=row["table_name"],
        old_target_table_name=old_table,
        new_target_table_name=new_table,
        source_tables=_split_csv(row["source_tables"]),
        old_transformation_script_path=row["old_transformation_script_path"],
        new_transformation_script_path=row["new_transformation_script_path"],
        owner_users=_split_csv(row["owner_users"]),
        support_team=row["support_team"],
        business_description=row["business_description"],
        criticality=row["criticality"],
        column_mapping=column_mapping,
        full_column_mapping=full_column_mapping,
    )


def _load_excels() -> None:
    if not METADATA_PATH.exists() or not MAPPING_PATH.exists():
        raise RuntimeError("required Excel fixtures are missing; run scripts/generate_excel_fixtures.py")
    metadata_df = pd.read_excel(METADATA_PATH)
    mapping_df = pd.read_excel(MAPPING_PATH)
    if "mapping_status" not in mapping_df.columns:
        mapping_df["mapping_status"] = "renamed"
    if "remarks" not in mapping_df.columns:
        mapping_df["remarks"] = ""
    metadata_df["division_key"] = metadata_df["division"].map(normalize_key)
    metadata_df["table_key"] = metadata_df["table_name"].map(normalize_key)
    mapping_df["old_table_key"] = mapping_df["old_table_name"].map(normalize_key)
    mapping_df["new_table_key"] = mapping_df["new_table_name"].map(normalize_key)
    mapping_df["old_column_key"] = mapping_df["old_column_name"].map(normalize_key)
    mapping_df["new_column_key"] = mapping_df["new_column_name"].map(normalize_key)
    mapping_df = mapping_df.fillna("")
    metadata_df = metadata_df.fillna("")
    STATE.update({"metadata_df": metadata_df, "mapping_df": mapping_df, "ready": True})
    LOGGER.info("loaded metadata rows=%s mapping rows=%s", len(metadata_df), len(mapping_df))


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return dedupe([item.strip() for item in str(value).split(",") if item.strip()])


def _serialize_mapping_rows(dataframe: pd.DataFrame) -> List[ColumnMappingRecord]:
    return [
        ColumnMappingRecord(
            old_system=item["old_system"],
            new_system=item["new_system"],
            old_table_name=item["old_table_name"],
            new_table_name=item["new_table_name"],
            old_column_name=item["old_column_name"],
            new_column_name=item["new_column_name"],
            data_type_old=item["data_type_old"],
            data_type_new=item["data_type_new"],
            mapping_status=item.get("mapping_status", "renamed") or "renamed",
            remarks=item.get("remarks", "") or "",
        )
        for item in dataframe.to_dict(orient="records")
    ]
