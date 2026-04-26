import json
import random
from calendar import monthrange
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import OBSERVABILITY_ROOT


SAMPLE_KQL_QUERIES = [
    """ADFPipelineRun
| where TimeGenerated >= ago(30d)
| where Status in ("Succeeded", "Failed", "Cancelled")
| summarize SuccessRate = round(100.0 * countif(Status == "Succeeded") / count(), 1), CompletedRuns = count() by PipelineName
| order by SuccessRate asc""",
    """// Schedule type is joined from app metadata in this POC.
ADFPipelineRun
| where TimeGenerated >= ago(30d)
| summarize RunCount = count() by PipelineName
| order by RunCount desc""",
    """ADFPipelineRun
| where TimeGenerated >= ago(30d)
| where Status in ("Succeeded", "Failed", "Cancelled")
| summarize AvgDurationMinutes = avg(DurationInMs / 60000.0) by bin(Start, 1d), PipelineName
| order by Start asc""",
]


PIPELINE_BLUEPRINTS = [
    {
        "pipeline_name": "DailySalesIngestion",
        "pipeline_id": "pipe-d-001",
        "cadence": "daily",
        "owner": "Retail Data Ops",
        "criticality": "high",
        "business_domain": "Sales",
        "schedule_timezone": "UTC",
        "schedule_time": "01:15",
        "scenario_profile": "healthy_stable",
        "trigger_name": "daily-sales-ingestion-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/DailySalesIngestion",
        "day_of_week": None,
        "day_of_month": None,
        "duration_range_minutes": (8, 14),
    },
    {
        "pipeline_name": "DailyCustomerIngestion",
        "pipeline_id": "pipe-d-002",
        "cadence": "daily",
        "owner": "Customer Insights",
        "criticality": "high",
        "business_domain": "Customer",
        "schedule_timezone": "UTC",
        "schedule_time": "02:10",
        "scenario_profile": "duration_regression",
        "trigger_name": "daily-customer-ingestion-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/DailyCustomerIngestion",
        "day_of_week": None,
        "day_of_month": None,
        "duration_range_minutes": (10, 18),
    },
    {
        "pipeline_name": "DailyFinanceReconciliation",
        "pipeline_id": "pipe-d-003",
        "cadence": "daily",
        "owner": "Finance Platform",
        "criticality": "medium",
        "business_domain": "Finance",
        "schedule_timezone": "UTC",
        "schedule_time": "03:05",
        "scenario_profile": "intermittent_failures",
        "trigger_name": "daily-finance-reconciliation-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/DailyFinanceReconciliation",
        "day_of_week": None,
        "day_of_month": None,
        "duration_range_minutes": (12, 20),
    },
    {
        "pipeline_name": "WeeklyInventorySnapshot",
        "pipeline_id": "pipe-w-001",
        "cadence": "weekly",
        "owner": "Supply Chain Data",
        "criticality": "medium",
        "business_domain": "Inventory",
        "schedule_timezone": "UTC",
        "schedule_time": "04:20",
        "scenario_profile": "recovered_after_failure",
        "trigger_name": "weekly-inventory-snapshot-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/WeeklyInventorySnapshot",
        "day_of_week": "tuesday",
        "day_of_month": None,
        "duration_range_minutes": (24, 42),
    },
    {
        "pipeline_name": "WeeklyOrdersBackfill",
        "pipeline_id": "pipe-w-002",
        "cadence": "weekly",
        "owner": "Retail Data Ops",
        "criticality": "medium",
        "business_domain": "Orders",
        "schedule_timezone": "UTC",
        "schedule_time": "05:30",
        "scenario_profile": "duration_regression",
        "trigger_name": "weekly-orders-backfill-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/WeeklyOrdersBackfill",
        "day_of_week": "monday",
        "day_of_month": None,
        "duration_range_minutes": (35, 55),
    },
    {
        "pipeline_name": "WeeklyRiskAggregation",
        "pipeline_id": "pipe-w-003",
        "cadence": "weekly",
        "owner": "Risk Analytics",
        "criticality": "high",
        "business_domain": "Risk",
        "schedule_timezone": "UTC",
        "schedule_time": "07:10",
        "scenario_profile": "missed_schedule",
        "trigger_name": "weekly-risk-aggregation-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/WeeklyRiskAggregation",
        "day_of_week": "friday",
        "day_of_month": None,
        "duration_range_minutes": (25, 50),
    },
    {
        "pipeline_name": "MonthlyRevenueClose",
        "pipeline_id": "pipe-m-001",
        "cadence": "monthly",
        "owner": "Finance Close Team",
        "criticality": "high",
        "business_domain": "Revenue",
        "schedule_timezone": "UTC",
        "schedule_time": "01:00",
        "scenario_profile": "healthy_stable",
        "trigger_name": "monthly-revenue-close-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/MonthlyRevenueClose",
        "day_of_week": None,
        "day_of_month": 3,
        "duration_range_minutes": (75, 120),
    },
    {
        "pipeline_name": "MonthlyComplianceRollup",
        "pipeline_id": "pipe-m-002",
        "cadence": "monthly",
        "owner": "Compliance Reporting",
        "criticality": "high",
        "business_domain": "Compliance",
        "schedule_timezone": "UTC",
        "schedule_time": "09:30",
        "scenario_profile": "repeated_failures",
        "trigger_name": "monthly-compliance-rollup-schedule",
        "resource_id": "/subscriptions/mock-sub/resourceGroups/mock-rg/providers/Microsoft.DataFactory/factories/demo-factory/pipelines/MonthlyComplianceRollup",
        "day_of_week": None,
        "day_of_month": 20,
        "duration_range_minutes": (90, 180),
    },
]

DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def build_observability_fixture_bundle(seed: int = 29, now_utc: Optional[datetime] = None) -> Dict[str, List[dict]]:
    rng = random.Random(seed)
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    metadata = [dict(item) for item in PIPELINE_BLUEPRINTS]
    trigger_rows: List[dict] = []
    pipeline_rows: List[dict] = []
    activity_rows: List[dict] = []

    for blueprint in metadata:
        scheduled_starts = _generate_schedule_starts(blueprint, now)
        for occurrence_index, scheduled_start in enumerate(scheduled_starts):
            if _should_skip_occurrence(blueprint["scenario_profile"], occurrence_index):
                continue

            scheduled_run = _build_pipeline_run(
                rng=rng,
                blueprint=blueprint,
                occurrence_index=occurrence_index,
                start=scheduled_start,
                now=now,
                trigger_type="Schedule",
                retry_attempt=0,
            )
            trigger_rows.append(scheduled_run["trigger"])
            pipeline_rows.append(scheduled_run["pipeline"])
            activity_rows.extend(scheduled_run["activities"])

            retry_run = _maybe_build_retry_run(
                rng=rng,
                blueprint=blueprint,
                scheduled_run=scheduled_run,
                occurrence_index=occurrence_index,
                now=now,
            )
            if retry_run:
                trigger_rows.append(retry_run["trigger"])
                pipeline_rows.append(retry_run["pipeline"])
                activity_rows.extend(retry_run["activities"])

    _maybe_add_in_progress_backfill(rng, metadata[4], now, trigger_rows, pipeline_rows, activity_rows)

    trigger_rows.sort(key=lambda row: row["Start"], reverse=True)
    pipeline_rows.sort(key=lambda row: row["Start"], reverse=True)
    activity_rows.sort(key=lambda row: row["Start"], reverse=True)

    return {
        "pipeline_metadata": metadata,
        "ADFTriggerRun": trigger_rows,
        "ADFPipelineRun": pipeline_rows,
        "ADFActivityRun": activity_rows,
        "sample_kql_queries": SAMPLE_KQL_QUERIES,
        "generated_at": _to_iso(now),
        "seed": seed,
    }


def write_observability_fixture_bundle(bundle: Dict[str, List[dict]], root: Path = OBSERVABILITY_ROOT) -> Dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "metadata": root / "pipeline_metadata.json",
        "trigger": root / "ADFTriggerRun.json",
        "pipeline": root / "ADFPipelineRun.json",
        "activity": root / "ADFActivityRun.json",
        "manifest": root / "manifest.json",
    }
    paths["metadata"].write_text(json.dumps(bundle["pipeline_metadata"], indent=2), encoding="utf-8")
    paths["trigger"].write_text(json.dumps(bundle["ADFTriggerRun"], indent=2), encoding="utf-8")
    paths["pipeline"].write_text(json.dumps(bundle["ADFPipelineRun"], indent=2), encoding="utf-8")
    paths["activity"].write_text(json.dumps(bundle["ADFActivityRun"], indent=2), encoding="utf-8")
    manifest = {
        "generated_at": bundle["generated_at"],
        "seed": bundle["seed"],
        "pipeline_count": len(bundle["pipeline_metadata"]),
        "trigger_rows": len(bundle["ADFTriggerRun"]),
        "pipeline_rows": len(bundle["ADFPipelineRun"]),
        "activity_rows": len(bundle["ADFActivityRun"]),
        "sample_kql_queries": bundle["sample_kql_queries"],
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return paths


def _generate_schedule_starts(blueprint: dict, now: datetime) -> List[datetime]:
    hour, minute = (int(part) for part in blueprint["schedule_time"].split(":"))
    starts: List[datetime] = []
    cadence = blueprint["cadence"]
    if cadence == "daily":
        for days_back in range(45):
            starts.append(
                datetime.combine((now - timedelta(days=days_back)).date(), time(hour=hour, minute=minute), tzinfo=timezone.utc)
            )
    elif cadence == "weekly":
        target_weekday = DAY_INDEX[blueprint["day_of_week"]]
        current = datetime.combine(now.date(), time(hour=hour, minute=minute), tzinfo=timezone.utc)
        delta_days = (current.weekday() - target_weekday) % 7
        first = current - timedelta(days=delta_days)
        if first > now:
            first -= timedelta(days=7)
        for weeks_back in range(20):
            starts.append(first - timedelta(weeks=weeks_back))
    else:
        for months_back in range(15):
            year, month = _shift_month(now.year, now.month, months_back)
            day = min(blueprint["day_of_month"], monthrange(year, month)[1])
            starts.append(datetime(year, month, day, hour, minute, tzinfo=timezone.utc))
    return [item for item in starts if item <= now]


def _build_pipeline_run(
    rng: random.Random,
    blueprint: dict,
    occurrence_index: int,
    start: datetime,
    now: datetime,
    trigger_type: str,
    retry_attempt: int,
) -> Dict[str, object]:
    status = _pick_status(blueprint["scenario_profile"], occurrence_index, trigger_type)
    duration_minutes = _pick_duration_minutes(rng, blueprint, occurrence_index, status, trigger_attempt=retry_attempt)
    end = None if status == "InProgress" else start + timedelta(minutes=duration_minutes)
    correlation_id = f"corr-{blueprint['pipeline_id']}-{occurrence_index}"
    trigger_run_id = f"trigger-{blueprint['pipeline_id']}-{occurrence_index}-{trigger_type.lower()}-{retry_attempt}"
    run_id = f"run-{blueprint['pipeline_id']}-{occurrence_index}-{trigger_type.lower()}-{retry_attempt}"
    failure_type, error_message = _failure_details(blueprint["scenario_profile"], status)

    trigger_row = {
        "TimeGenerated": _to_iso(end or now),
        "TriggerRunId": trigger_run_id,
        "TriggerName": blueprint["trigger_name"] if trigger_type == "Schedule" else f"{blueprint['trigger_name']}-retry",
        "TriggerType": trigger_type,
        "Status": status,
        "Start": _to_iso(start),
        "End": _to_iso(end) if end else None,
        "PipelineName": blueprint["pipeline_name"],
        "CorrelationId": correlation_id,
        "RetryAttempt": retry_attempt,
        "ResourceId": blueprint["resource_id"],
    }
    pipeline_row = {
        "TimeGenerated": _to_iso(end or now),
        "RunId": run_id,
        "PipelineName": blueprint["pipeline_name"],
        "Status": status,
        "Start": _to_iso(start),
        "End": _to_iso(end) if end else None,
        "DurationInMs": None if status == "InProgress" else int(duration_minutes * 60 * 1000),
        "FailureType": failure_type,
        "ErrorMessage": error_message,
        "CorrelationId": correlation_id,
        "TriggerRunId": trigger_run_id,
        "TriggerType": trigger_type,
        "RetryAttempt": retry_attempt,
        "ResourceId": blueprint["resource_id"],
    }
    activities = _build_activities(
        rng=rng,
        blueprint=blueprint,
        run_id=run_id,
        start=start,
        end=end,
        status=status,
        error_message=error_message,
        retry_attempt=retry_attempt,
    )
    return {"trigger": trigger_row, "pipeline": pipeline_row, "activities": activities}


def _build_activities(
    rng: random.Random,
    blueprint: dict,
    run_id: str,
    start: datetime,
    end: Optional[datetime],
    status: str,
    error_message: Optional[str],
    retry_attempt: int,
) -> List[dict]:
    activity_templates = [
        ("ExtractSource", "Copy"),
        ("ValidateSource", "Validation"),
        ("TransformBusinessRules", "DataFlow"),
        ("LoadTarget", "Copy"),
        ("PublishMetrics", "StoredProcedure"),
        ("NotifySteward", "Web"),
    ]
    activity_count = rng.randint(2, 6)
    chosen = activity_templates[:activity_count]
    total_seconds = max(120, int((end - start).total_seconds())) if end else 600
    remaining = total_seconds
    current = start
    rows = []
    failed_index = activity_count - 1 if status == "Failed" else None
    cancelled_index = max(1, activity_count - 1) if status == "Cancelled" else None
    for index, (name, activity_type) in enumerate(chosen):
        if index == activity_count - 1:
            duration_seconds = max(60, remaining)
        else:
            duration_seconds = max(60, int(remaining * rng.uniform(0.12, 0.28)))
            remaining -= duration_seconds
        activity_start = current
        activity_end = None if status == "InProgress" and index == activity_count - 1 else activity_start + timedelta(seconds=duration_seconds)
        current = activity_end or activity_start
        if failed_index is not None:
            activity_status = "Failed" if index == failed_index else "Succeeded"
        elif cancelled_index is not None:
            activity_status = "Cancelled" if index >= cancelled_index else "Succeeded"
        elif status == "InProgress" and index == activity_count - 1:
            activity_status = "InProgress"
        else:
            activity_status = "Succeeded"
        rows.append(
            {
                "TimeGenerated": _to_iso(activity_end or activity_start),
                "ActivityRunId": f"{run_id}-activity-{index + 1}",
                "RunId": run_id,
                "ActivityName": name,
                "ActivityType": activity_type,
                "Status": activity_status,
                "Start": _to_iso(activity_start),
                "End": _to_iso(activity_end) if activity_end else None,
                "DurationInMs": None if activity_status == "InProgress" else duration_seconds * 1000,
                "ErrorMessage": error_message if activity_status == "Failed" else None,
                "RetryAttempt": retry_attempt,
                "ResourceId": blueprint["resource_id"],
            }
        )
    return rows


def _maybe_build_retry_run(
    rng: random.Random,
    blueprint: dict,
    scheduled_run: Dict[str, object],
    occurrence_index: int,
    now: datetime,
) -> Optional[Dict[str, object]]:
    scheduled_status = scheduled_run["pipeline"]["Status"]
    scenario = blueprint["scenario_profile"]
    if scheduled_status not in {"Failed", "Cancelled"}:
        return None
    if scenario not in {"intermittent_failures", "repeated_failures"}:
        return None
    retry_start = _parse_iso(scheduled_run["pipeline"]["End"]) + timedelta(minutes=25)
    if retry_start >= now:
        return None
    return _build_pipeline_run(
        rng=rng,
        blueprint=blueprint,
        occurrence_index=occurrence_index,
        start=retry_start,
        now=now,
        trigger_type="Manual",
        retry_attempt=1,
    )


def _maybe_add_in_progress_backfill(
    rng: random.Random,
    blueprint: dict,
    now: datetime,
    trigger_rows: List[dict],
    pipeline_rows: List[dict],
    activity_rows: List[dict],
) -> None:
    start = now - timedelta(minutes=18)
    in_progress_run = _build_pipeline_run(
        rng=rng,
        blueprint=blueprint,
        occurrence_index=999,
        start=start,
        now=now,
        trigger_type="Manual",
        retry_attempt=0,
    )
    in_progress_run["trigger"]["Status"] = "InProgress"
    in_progress_run["trigger"]["End"] = None
    in_progress_run["trigger"]["TimeGenerated"] = _to_iso(now)
    in_progress_run["pipeline"]["Status"] = "InProgress"
    in_progress_run["pipeline"]["End"] = None
    in_progress_run["pipeline"]["DurationInMs"] = None
    in_progress_run["pipeline"]["FailureType"] = None
    in_progress_run["pipeline"]["ErrorMessage"] = None
    in_progress_run["pipeline"]["TimeGenerated"] = _to_iso(now)
    if in_progress_run["activities"]:
        in_progress_run["activities"][-1]["Status"] = "InProgress"
        in_progress_run["activities"][-1]["End"] = None
        in_progress_run["activities"][-1]["DurationInMs"] = None
        in_progress_run["activities"][-1]["TimeGenerated"] = _to_iso(now)
    trigger_rows.append(in_progress_run["trigger"])
    pipeline_rows.append(in_progress_run["pipeline"])
    activity_rows.extend(in_progress_run["activities"])


def _pick_status(scenario_profile: str, occurrence_index: int, trigger_type: str) -> str:
    if trigger_type == "Manual":
        return "InProgress" if occurrence_index == 999 else "Succeeded"
    if scenario_profile == "healthy_stable":
        return "Succeeded"
    if scenario_profile == "duration_regression":
        return "Cancelled" if occurrence_index == 10 else "Succeeded"
    if scenario_profile == "intermittent_failures":
        if occurrence_index in {2, 8, 13, 21}:
            return "Failed"
        return "Succeeded"
    if scenario_profile == "repeated_failures":
        if occurrence_index in {0, 1, 2}:
            return "Failed"
        if occurrence_index == 4:
            return "Cancelled"
        return "Succeeded"
    if scenario_profile == "missed_schedule":
        return "Succeeded"
    if scenario_profile == "recovered_after_failure":
        if occurrence_index == 1:
            return "Failed"
        return "Succeeded"
    return "Succeeded"


def _pick_duration_minutes(
    rng: random.Random,
    blueprint: dict,
    occurrence_index: int,
    status: str,
    trigger_attempt: int,
) -> int:
    minimum, maximum = blueprint["duration_range_minutes"]
    base = rng.randint(minimum, maximum)
    if blueprint["scenario_profile"] == "duration_regression" and occurrence_index < 7:
        base = int(base * rng.uniform(1.25, 1.55))
    if blueprint["scenario_profile"] == "repeated_failures" and occurrence_index < 3:
        base = int(base * rng.uniform(0.55, 0.8))
    if blueprint["scenario_profile"] == "recovered_after_failure" and occurrence_index == 0:
        base = int(base * 1.1)
    if trigger_attempt > 0:
        base = max(minimum, int(base * 0.85))
    if status == "Cancelled":
        return max(minimum // 2, int(base * 0.6))
    if status == "Failed":
        return max(minimum, int(base * 0.7))
    return base


def _failure_details(scenario_profile: str, status: str) -> tuple[Optional[str], Optional[str]]:
    if status == "Failed":
        if scenario_profile == "repeated_failures":
            return "UserError", "Target sink timed out while waiting for downstream acknowledgement."
        if scenario_profile == "intermittent_failures":
            return "SystemError", "Source dataset returned transient 429 throttling responses."
        return "SystemError", "Pipeline failed during transformation validation."
    if status == "Cancelled":
        return "SystemError", "Pipeline exceeded the orchestrator timeout threshold and was cancelled."
    return None, None


def _should_skip_occurrence(scenario_profile: str, occurrence_index: int) -> bool:
    return scenario_profile == "missed_schedule" and occurrence_index == 0


def _shift_month(year: int, month: int, months_back: int) -> tuple[int, int]:
    absolute = year * 12 + (month - 1) - months_back
    shifted_year, shifted_month_index = divmod(absolute, 12)
    return shifted_year, shifted_month_index + 1


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
