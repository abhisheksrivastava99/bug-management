import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import OBSERVABILITY_ROOT
from .llm import OpenAIChatClient
from .observability_models import (
    AdfActivityRunRecord,
    AdfPipelineRunRecord,
    AdfTriggerRunRecord,
    AttentionState,
    ObservabilityAttentionItem,
    ObservabilityCadenceGroup,
    ObservabilityFailureEvent,
    ObservabilityFilters,
    ObservabilityPipelineDetailResponse,
    ObservabilityPipelineMetadata,
    ObservabilityPipelineRow,
    ObservabilityPipelinesResponse,
    ObservabilityQueryPlan,
    ObservabilityQueryRequest,
    ObservabilityQueryResponse,
    ObservabilityQueryResult,
    ObservabilityRetrySummary,
    ObservabilityRunHistoryItem,
    ObservabilitySummaryAIRequest,
    ObservabilitySummaryAIResponse,
    ObservabilitySummaryMetric,
    ObservabilitySummaryResponse,
    ObservabilityTrendPoint,
    ObservabilityActivitySummaryItem,
)
from .observability_prompt_pack import (
    build_query_summary_prompt,
    build_query_translation_prompt,
    build_summary_prompt,
)


LOGGER = logging.getLogger(__name__)
CADENCE_LABELS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
CADENCE_WINDOWS = {"daily": 30, "weekly": 84, "monthly": 365}
STALE_THRESHOLDS = {"daily": 36, "weekly": 168, "monthly": 960}
TERMINAL_STATUSES = {"Succeeded", "Failed", "Cancelled"}
ALLOWED_INTENTS = {
    "success_rate_by_pipeline",
    "run_count_by_cadence",
    "average_duration_trend",
    "recent_failures",
    "slowest_pipelines",
    "pipelines_with_retries",
    "last_run_status",
    "unsupported",
}


class MockObservabilityProvider:
    def __init__(self, root: Path = OBSERVABILITY_ROOT) -> None:
        self.root = root

    def load(self) -> Dict[str, list]:
        metadata_path = self.root / "pipeline_metadata.json"
        trigger_path = self.root / "ADFTriggerRun.json"
        pipeline_path = self.root / "ADFPipelineRun.json"
        activity_path = self.root / "ADFActivityRun.json"
        if not all(path.exists() for path in [metadata_path, trigger_path, pipeline_path, activity_path]):
            raise FileNotFoundError(
                f"Observability fixtures are missing in {self.root}. Run python3 scripts/generate_observability_fixtures.py."
            )
        metadata = [ObservabilityPipelineMetadata(**row) for row in json.loads(metadata_path.read_text(encoding="utf-8"))]
        triggers = [AdfTriggerRunRecord(**row) for row in json.loads(trigger_path.read_text(encoding="utf-8"))]
        pipelines = [AdfPipelineRunRecord(**row) for row in json.loads(pipeline_path.read_text(encoding="utf-8"))]
        activities = [AdfActivityRunRecord(**row) for row in json.loads(activity_path.read_text(encoding="utf-8"))]
        return {
            "metadata": metadata,
            "triggers": triggers,
            "pipelines": pipelines,
            "activities": activities,
        }


class ObservabilityService:
    def __init__(self, provider: Optional[MockObservabilityProvider] = None, llm_client: Optional[OpenAIChatClient] = None) -> None:
        configured_source = os.getenv("BM_OBSERVABILITY_DATA_SOURCE", "mock").lower()
        if provider is None and configured_source != "mock":
            LOGGER.warning("Unsupported observability data source '%s'; falling back to mock fixtures.", configured_source)
        self.provider = provider or MockObservabilityProvider()
        self.llm_client = llm_client or OpenAIChatClient()

    def get_summary(self, filters: ObservabilityFilters) -> ObservabilitySummaryResponse:
        contexts, now = self._build_pipeline_contexts(filters)
        attention_items = self._build_attention_inbox(contexts)
        top_regressions = sorted(
            [item["row"] for item in contexts if item["row"].duration_delta_pct and item["row"].duration_delta_pct > 0],
            key=lambda row: row.duration_delta_pct or 0,
            reverse=True,
        )[:5]
        recent_failures = sorted(
            [
                ObservabilityFailureEvent(
                    pipeline_name=item["row"].pipeline_name,
                    cadence=item["row"].cadence,
                    status=item["latest_failure"].Status,
                    started_at=item["latest_failure"].Start,
                    error_message=item["latest_failure"].ErrorMessage,
                )
                for item in contexts
                if item["latest_failure"] and self._within_window(item["latest_failure"].Start, now, filters.window_days)
            ],
            key=lambda event: event.started_at,
            reverse=True,
        )[:6]
        visible_terminal_runs = [
            run
            for item in contexts
            for run in item["visible_terminal_runs"]
        ]
        success_count = sum(1 for run in visible_terminal_runs if run.Status == "Succeeded")
        success_rate = round((success_count / len(visible_terminal_runs)) * 100, 1) if visible_terminal_runs else 100.0
        failure_count = sum(1 for run in visible_terminal_runs if run.Status in {"Failed", "Cancelled"})
        delta_values = [item["row"].duration_delta_pct for item in contexts if item["row"].duration_delta_pct is not None]
        avg_delta = round(sum(delta_values) / len(delta_values), 1) if delta_values else 0.0
        needing_attention = sum(1 for item in contexts if item["row"].attention_state in {"attention", "watch"})
        summary_metrics = [
            ObservabilitySummaryMetric(label="Total Pipelines", value=str(len(contexts)), raw_value=float(len(contexts))),
            ObservabilitySummaryMetric(
                label="Pipelines Needing Attention",
                value=str(needing_attention),
                raw_value=float(needing_attention),
                tone="warning" if needing_attention else "positive",
            ),
            ObservabilitySummaryMetric(
                label="Success Rate",
                value=f"{success_rate:.1f}%",
                raw_value=success_rate,
                tone="positive" if success_rate >= 95 else "warning",
            ),
            ObservabilitySummaryMetric(
                label="Avg Duration Delta",
                value=f"{avg_delta:+.1f}%",
                raw_value=avg_delta,
                tone="warning" if avg_delta > 10 else "neutral",
            ),
            ObservabilitySummaryMetric(
                label="Failure Count",
                value=str(failure_count),
                raw_value=float(failure_count),
                tone="warning" if failure_count else "positive",
            ),
        ]
        return ObservabilitySummaryResponse(
            generated_at=_to_iso(now),
            filters=filters,
            summary_metrics=summary_metrics,
            attention_items=attention_items,
            top_regressions=top_regressions,
            recent_failures=recent_failures,
        )

    def get_pipelines(self, filters: ObservabilityFilters) -> ObservabilityPipelinesResponse:
        contexts, now = self._build_pipeline_contexts(filters)
        groups = []
        for cadence in ["daily", "weekly", "monthly"]:
            group_rows = [item["row"] for item in contexts if item["row"].cadence == cadence]
            groups.append(
                ObservabilityCadenceGroup(
                    cadence=cadence,
                    label=CADENCE_LABELS[cadence],
                    total_count=len(group_rows),
                    attention_count=sum(1 for row in group_rows if row.attention_state in {"attention", "watch"}),
                    pipelines=group_rows,
                )
            )
        total_count = len(self.provider.load()["metadata"])
        return ObservabilityPipelinesResponse(
            generated_at=_to_iso(now),
            filters=filters,
            total_pipeline_count=total_count,
            filtered_pipeline_count=len(contexts),
            groups=groups,
        )

    def get_pipeline_detail(self, pipeline_name: str, filters: ObservabilityFilters) -> ObservabilityPipelineDetailResponse:
        contexts, now = self._build_pipeline_contexts(filters)
        match = next((item for item in contexts if item["row"].pipeline_name == pipeline_name), None)
        if not match:
            raise KeyError(f"Pipeline not found: {pipeline_name}")
        run_history = [
            ObservabilityRunHistoryItem(
                run_id=run.RunId,
                trigger_type=run.TriggerType,
                status=run.Status,
                start=run.Start,
                end=run.End,
                duration_seconds=_duration_seconds(run.DurationInMs),
                retry_attempt=run.RetryAttempt,
                error_message=run.ErrorMessage,
                is_scheduled=run.TriggerType == "Schedule",
            )
            for run in match["all_runs"][:12]
        ]
        scheduled_completed = [run for run in match["terminal_scheduled_runs"][:10]]
        duration_trend = [
            ObservabilityTrendPoint(
                label=_parse_iso(run.Start).strftime("%b %d"),
                start=run.Start,
                duration_seconds=_duration_seconds(run.DurationInMs),
                status=run.Status,
            )
            for run in reversed(scheduled_completed)
        ]
        retry_runs = [
            ObservabilityRunHistoryItem(
                run_id=run.RunId,
                trigger_type=run.TriggerType,
                status=run.Status,
                start=run.Start,
                end=run.End,
                duration_seconds=_duration_seconds(run.DurationInMs),
                retry_attempt=run.RetryAttempt,
                error_message=run.ErrorMessage,
                is_scheduled=False,
            )
            for run in match["retry_runs"][:5]
        ]
        activity_summary = self._build_activity_summary(match["activity_runs"], match["terminal_scheduled_runs"][:5])
        return ObservabilityPipelineDetailResponse(
            generated_at=_to_iso(now),
            filters=filters,
            pipeline=match["row"],
            attention_items=self._build_attention_items(match),
            run_history=run_history,
            duration_trend=duration_trend,
            latest_failure=(
                ObservabilityRunHistoryItem(
                    run_id=match["latest_failure"].RunId,
                    trigger_type=match["latest_failure"].TriggerType,
                    status=match["latest_failure"].Status,
                    start=match["latest_failure"].Start,
                    end=match["latest_failure"].End,
                    duration_seconds=_duration_seconds(match["latest_failure"].DurationInMs),
                    retry_attempt=match["latest_failure"].RetryAttempt,
                    error_message=match["latest_failure"].ErrorMessage,
                    is_scheduled=match["latest_failure"].TriggerType == "Schedule",
                )
                if match["latest_failure"]
                else None
            ),
            retry_summary=ObservabilityRetrySummary(
                total_retries=len(match["retry_runs"]),
                latest_retry_at=match["retry_runs"][0].Start if match["retry_runs"] else None,
                recent_retry_runs=retry_runs,
            ),
            activity_summary=activity_summary,
        )

    async def get_summary_ai(self, request: ObservabilitySummaryAIRequest) -> ObservabilitySummaryAIResponse:
        fallback = self._fallback_dashboard_summary(request.summary, request.groups)
        if not self.llm_client.enabled:
            return fallback
        prompt = build_summary_prompt(request.summary, request.groups)
        payload = await self.llm_client.complete_json(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            debug_label="observability-summary",
        )
        if not payload:
            return fallback
        try:
            return ObservabilitySummaryAIResponse(
                title=payload["title"],
                summary=payload["summary"],
                insights=payload.get("insights", []),
                caveat=payload.get("caveat"),
                used_fallback=False,
            )
        except KeyError:
            return fallback

    async def run_query(self, request: ObservabilityQueryRequest) -> ObservabilityQueryResponse:
        plan, display_kql, warnings, used_translation_fallback = await self._build_query_plan(request)
        result = self._execute_query_plan(plan, request.filters)
        summary, insights, caveats, follow_ups, used_summary_fallback = await self._summarize_query_result(
            request.question,
            result,
            warnings,
        )
        return ObservabilityQueryResponse(
            question=request.question,
            display_kql=display_kql,
            query_plan=plan,
            result=result,
            summary=summary,
            insights=insights,
            caveats=caveats,
            follow_ups=follow_ups,
            warnings=warnings,
            used_fallback=used_translation_fallback or used_summary_fallback,
        )

    async def _build_query_plan(
        self,
        request: ObservabilityQueryRequest,
    ) -> Tuple[ObservabilityQueryPlan, str, List[str], bool]:
        fallback_plan, fallback_kql, fallback_warnings = self._deterministic_query_plan(request.question, request.filters)
        if not self.llm_client.enabled:
            return fallback_plan, fallback_kql, fallback_warnings, True

        prompt = build_query_translation_prompt(request.question, request.filters.dict())
        payload = await self.llm_client.complete_json(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            debug_label="observability-query-translation",
        )
        if not payload:
            return fallback_plan, fallback_kql, fallback_warnings, True
        try:
            if payload.get("intent") not in ALLOWED_INTENTS:
                return fallback_plan, fallback_kql, fallback_warnings, True
            plan = ObservabilityQueryPlan(
                intent=payload["intent"],
                dataset=payload.get("dataset", "pipeline_runs"),
                metric=payload.get("metric", fallback_plan.metric),
                time_window_days=max(1, min(int(payload.get("time_window_days", request.filters.window_days)), 365)),
                cadence=payload.get("cadence"),
                pipeline_name=payload.get("pipeline_name"),
                group_by=payload.get("group_by", []),
                filters=payload.get("filters", {}),
                sort_field=payload.get("sort_field"),
                sort_direction=payload.get("sort_direction", "desc"),
                limit=max(1, min(int(payload.get("limit", 10)), 25)),
                visualization=payload.get("visualization"),
            )
            display_kql = payload.get("display_kql", fallback_kql)
            warnings = list(dict.fromkeys(fallback_warnings + payload.get("warnings", [])))
            return plan, display_kql, warnings, False
        except Exception:
            return fallback_plan, fallback_kql, fallback_warnings, True

    async def _summarize_query_result(
        self,
        question: str,
        result: ObservabilityQueryResult,
        warnings: List[str],
    ) -> Tuple[str, List[str], List[str], List[str], bool]:
        fallback = self._fallback_query_summary(question, result, warnings)
        if not self.llm_client.enabled:
            return (*fallback, True)
        prompt = build_query_summary_prompt(question, result, warnings)
        payload = await self.llm_client.complete_json(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            debug_label="observability-query-summary",
        )
        if not payload:
            return (*fallback, True)
        try:
            return (
                payload["summary"],
                payload.get("insights", []),
                payload.get("caveats", []),
                payload.get("follow_ups", []),
                False,
            )
        except KeyError:
            return (*fallback, True)

    def _build_pipeline_contexts(self, filters: ObservabilityFilters) -> Tuple[List[Dict[str, object]], datetime]:
        data = self.provider.load()
        now = datetime.now(timezone.utc)
        pipelines_by_name = defaultdict(list)
        activity_by_run_id = defaultdict(list)
        for run in data["pipelines"]:
            pipelines_by_name[run.PipelineName].append(run)
        for runs in pipelines_by_name.values():
            runs.sort(key=lambda item: item.Start, reverse=True)
        for activity in data["activities"]:
            activity_by_run_id[activity.RunId].append(activity)
        contexts: List[Dict[str, object]] = []
        for metadata in data["metadata"]:
            all_runs = pipelines_by_name.get(metadata.pipeline_name, [])
            scheduled_runs = [run for run in all_runs if run.TriggerType == "Schedule"]
            terminal_scheduled = [run for run in scheduled_runs if run.Status in TERMINAL_STATUSES]
            visible_terminal = [
                run
                for run in terminal_scheduled
                if self._within_window(run.Start, now, filters.window_days)
            ]
            health_window_days = CADENCE_WINDOWS[metadata.cadence]
            health_terminal = [
                run
                for run in terminal_scheduled
                if self._within_window(run.Start, now, health_window_days)
            ]
            latest_scheduled = scheduled_runs[0] if scheduled_runs else None
            latest_failure = next((run for run in scheduled_runs if run.Status in {"Failed", "Cancelled"}), None)
            history = [run for run in terminal_scheduled if run.DurationInMs is not None]
            last_7 = history[:7]
            prev_7 = history[7:14]
            avg_last_7 = _average_duration(last_7)
            avg_prev_7 = _average_duration(prev_7)
            delta_pct = None
            if avg_last_7 is not None and avg_prev_7 not in {None, 0}:
                delta_pct = round(((avg_last_7 - avg_prev_7) / avg_prev_7) * 100, 1)
            success_count = sum(1 for run in health_terminal if run.Status == "Succeeded")
            success_rate = round((success_count / len(health_terminal)) * 100, 1) if health_terminal else 100.0
            failure_count = sum(1 for run in health_terminal if run.Status in {"Failed", "Cancelled"})
            stale = not latest_scheduled or (now - _parse_iso(latest_scheduled.Start)).total_seconds() > STALE_THRESHOLDS[metadata.cadence] * 3600
            recovered = bool(
                latest_scheduled
                and latest_scheduled.Status == "Succeeded"
                and len(scheduled_runs) > 1
                and scheduled_runs[1].Status in {"Failed", "Cancelled"}
            )
            slowdown = bool(delta_pct is not None and delta_pct > 20 and (latest_scheduled and latest_scheduled.Status == "Succeeded"))
            primary_state, primary_reason = self._derive_attention_state(
                latest_scheduled.Status if latest_scheduled else "Failed",
                stale,
                slowdown,
                recovered,
            )
            row = ObservabilityPipelineRow(
                pipeline_name=metadata.pipeline_name,
                cadence=metadata.cadence,
                owner=metadata.owner,
                criticality=metadata.criticality,
                business_domain=metadata.business_domain,
                scenario_profile=metadata.scenario_profile,
                last_run_status=latest_scheduled.Status if latest_scheduled else "Failed",
                last_run_start=latest_scheduled.Start if latest_scheduled else None,
                last_run_end=latest_scheduled.End if latest_scheduled else None,
                last_run_duration_seconds=_duration_seconds(latest_scheduled.DurationInMs) if latest_scheduled else None,
                average_duration_last_7_runs=avg_last_7,
                average_duration_previous_7_runs=avg_prev_7,
                duration_delta_pct=delta_pct,
                success_rate_window=success_rate,
                failure_count_window=failure_count,
                latest_error_message=latest_failure.ErrorMessage if latest_failure else None,
                stale=stale,
                recovered_after_failure=recovered,
                attention_state=primary_state,
                attention_reason=primary_reason,
            )
            if not self._matches_filters(metadata, row, filters):
                continue
            contexts.append(
                {
                    "metadata": metadata,
                    "row": row,
                    "all_runs": all_runs,
                    "scheduled_runs": scheduled_runs,
                    "terminal_scheduled_runs": history,
                    "visible_terminal_runs": visible_terminal,
                    "latest_failure": latest_failure,
                    "retry_runs": [run for run in all_runs if run.RetryAttempt > 0],
                    "activity_runs": activity_by_run_id,
                    "slowdown": slowdown,
                }
            )
        contexts.sort(key=lambda item: (item["row"].cadence, item["row"].pipeline_name))
        return contexts, now

    def _build_activity_summary(
        self,
        activity_map: Dict[str, list],
        recent_runs: List[AdfPipelineRunRecord],
    ) -> List[ObservabilityActivitySummaryItem]:
        grouped: Dict[str, List[AdfActivityRunRecord]] = defaultdict(list)
        for run in recent_runs:
            for activity in activity_map.get(run.RunId, []):
                grouped[f"{activity.ActivityName}|{activity.ActivityType}"].append(activity)
        items = []
        for key, records in grouped.items():
            latest = max(records, key=lambda item: item.Start)
            average_seconds = _average_activity_duration(records)
            items.append(
                ObservabilityActivitySummaryItem(
                    activity_name=latest.ActivityName,
                    activity_type=latest.ActivityType,
                    latest_status=latest.Status,
                    average_duration_seconds=average_seconds,
                    runs_seen=len(records),
                    failure_count=sum(1 for record in records if record.Status == "Failed"),
                )
            )
        items.sort(key=lambda item: item.average_duration_seconds or 0, reverse=True)
        return items[:5]

    def _build_attention_inbox(self, contexts: List[Dict[str, object]]) -> List[ObservabilityAttentionItem]:
        items = [item for context in contexts for item in self._build_attention_items(context)]
        def sort_key(item: ObservabilityAttentionItem) -> tuple:
            priority = {
                "failed_last_run": 0,
                "missed_expected_schedule": 1,
                "slower_than_baseline": 2,
                "recovered_after_recent_failures": 3,
            }.get(item.kind, 4)
            return (priority, item.pipeline_name)

        return sorted(items, key=sort_key)[:8]

    def _build_attention_items(self, context: Dict[str, object]) -> List[ObservabilityAttentionItem]:
        row: ObservabilityPipelineRow = context["row"]
        items = []
        if row.last_run_status in {"Failed", "Cancelled"}:
            items.append(
                ObservabilityAttentionItem(
                    kind="failed_last_run",
                    pipeline_name=row.pipeline_name,
                    cadence=row.cadence,
                    title="Failed in last run",
                    description=row.latest_error_message or "The latest scheduled run did not complete successfully.",
                    status=row.last_run_status,
                    attention_state="attention",
                )
            )
        if row.stale:
            items.append(
                ObservabilityAttentionItem(
                    kind="missed_expected_schedule",
                    pipeline_name=row.pipeline_name,
                    cadence=row.cadence,
                    title="Missed expected schedule",
                    description="No scheduled run has landed within the expected cadence window.",
                    status=row.last_run_status,
                    attention_state="attention",
                )
            )
        if context["slowdown"]:
            items.append(
                ObservabilityAttentionItem(
                    kind="slower_than_baseline",
                    pipeline_name=row.pipeline_name,
                    cadence=row.cadence,
                    title="Running slower than baseline",
                    description=f"Last 7 runs are up {row.duration_delta_pct:.1f}% versus the prior 7-run baseline.",
                    status=row.last_run_status,
                    attention_state="watch",
                )
            )
        if row.recovered_after_failure:
            items.append(
                ObservabilityAttentionItem(
                    kind="recovered_after_recent_failures",
                    pipeline_name=row.pipeline_name,
                    cadence=row.cadence,
                    title="Recovered after recent failures",
                    description="The latest scheduled run succeeded after a recent failed run.",
                    status=row.last_run_status,
                    attention_state="recovered",
                )
            )
        return items

    def _deterministic_query_plan(self, question: str, filters: ObservabilityFilters) -> Tuple[ObservabilityQueryPlan, str, List[str]]:
        lowered = question.lower().strip()
        cadence = next((item for item in ["daily", "weekly", "monthly"] if item in lowered), filters.cadence)
        pipeline_name = self._extract_pipeline_name(question)
        warnings: List[str] = []
        if "success rate" in lowered:
            plan = ObservabilityQueryPlan(
                intent="success_rate_by_pipeline",
                dataset="pipeline_runs",
                metric="success_rate",
                time_window_days=filters.window_days,
                cadence=cadence,
                pipeline_name=pipeline_name,
                group_by=["pipeline_name"],
                sort_field="success_rate",
                sort_direction="asc",
                limit=10,
                visualization="table",
            )
        elif "run count" in lowered and ("schedule" in lowered or "cadence" in lowered or "type" in lowered):
            plan = ObservabilityQueryPlan(
                intent="run_count_by_cadence",
                dataset="pipeline_runs",
                metric="run_count",
                time_window_days=filters.window_days,
                group_by=["cadence"],
                limit=10,
                visualization="table",
            )
        elif "duration trend" in lowered or ("average duration" in lowered and "trend" in lowered):
            plan = ObservabilityQueryPlan(
                intent="average_duration_trend",
                dataset="pipeline_runs",
                metric="average_duration",
                time_window_days=filters.window_days,
                cadence=cadence,
                pipeline_name=pipeline_name,
                group_by=["day" if "day" in lowered or cadence == "daily" else "week"],
                limit=20,
                visualization="line",
            )
        elif "retry" in lowered:
            plan = ObservabilityQueryPlan(
                intent="pipelines_with_retries",
                dataset="pipeline_runs",
                metric="retry_count",
                time_window_days=filters.window_days,
                cadence=cadence,
                limit=10,
                visualization="table",
            )
        elif "slowest" in lowered or "slower" in lowered:
            plan = ObservabilityQueryPlan(
                intent="slowest_pipelines",
                dataset="pipeline_runs",
                metric="average_duration",
                time_window_days=filters.window_days,
                cadence=cadence,
                limit=10,
                visualization="table",
            )
        elif "last run" in lowered and "status" in lowered:
            plan = ObservabilityQueryPlan(
                intent="last_run_status",
                dataset="pipeline_runs",
                metric="last_run_status",
                time_window_days=filters.window_days,
                cadence=cadence,
                pipeline_name=pipeline_name,
                limit=1 if pipeline_name else 10,
                visualization="table",
            )
        elif "fail" in lowered:
            plan = ObservabilityQueryPlan(
                intent="recent_failures",
                dataset="pipeline_runs",
                metric="failure_count",
                time_window_days=filters.window_days,
                cadence=cadence,
                limit=10,
                visualization="table",
            )
        else:
            warnings.append("The request is outside the supported v1 query set, so a generic fallback was used.")
            plan = ObservabilityQueryPlan(
                intent="unsupported",
                dataset="pipeline_runs",
                metric="last_run_status",
                time_window_days=filters.window_days,
                cadence=cadence,
                limit=10,
                visualization="table",
            )
        display_kql = self._build_display_kql(plan)
        if pipeline_name and plan.intent != "last_run_status":
            plan.pipeline_name = pipeline_name
        return plan, display_kql, warnings

    def _execute_query_plan(self, plan: ObservabilityQueryPlan, base_filters: ObservabilityFilters) -> ObservabilityQueryResult:
        filters = _model_copy(base_filters, update={"window_days": plan.time_window_days})
        if plan.cadence:
            filters = _model_copy(filters, update={"cadence": plan.cadence})
        contexts, now = self._build_pipeline_contexts(filters)
        if plan.pipeline_name:
            contexts = [item for item in contexts if item["row"].pipeline_name.lower() == plan.pipeline_name.lower()]

        if plan.intent == "success_rate_by_pipeline":
            rows = []
            for item in contexts:
                visible_runs = item["visible_terminal_runs"]
                success = sum(1 for run in visible_runs if run.Status == "Succeeded")
                rate = round((success / len(visible_runs)) * 100, 1) if visible_runs else 100.0
                rows.append(
                    {
                        "pipeline_name": item["row"].pipeline_name,
                        "cadence": item["row"].cadence,
                        "success_rate": rate,
                        "completed_runs": len(visible_runs),
                    }
                )
            rows.sort(key=lambda row: row["success_rate"])
            return _query_result(["pipeline_name", "cadence", "success_rate", "completed_runs"], rows[: plan.limit], plan.visualization)

        if plan.intent == "run_count_by_cadence":
            counts = defaultdict(int)
            for item in contexts:
                counts[item["row"].cadence] += len(item["visible_terminal_runs"])
            rows = [{"cadence": cadence, "run_count": counts[cadence]} for cadence in ["daily", "weekly", "monthly"]]
            return _query_result(["cadence", "run_count"], rows, plan.visualization)

        if plan.intent == "average_duration_trend":
            buckets = defaultdict(list)
            grain = "day" if "day" in plan.group_by else "week"
            for item in contexts:
                for run in item["visible_terminal_runs"]:
                    if run.DurationInMs is None:
                        continue
                    started = _parse_iso(run.Start)
                    label = started.strftime("%Y-%m-%d") if grain == "day" else f"{started.isocalendar().year}-W{started.isocalendar().week:02d}"
                    buckets[label].append(run.DurationInMs / 60000.0)
            rows = [
                {"period": label, "avg_duration_minutes": round(sum(values) / len(values), 1), "completed_runs": len(values)}
                for label, values in sorted(buckets.items())
            ]
            return _query_result(["period", "avg_duration_minutes", "completed_runs"], rows, plan.visualization)

        if plan.intent == "recent_failures":
            rows = []
            for item in contexts:
                for run in item["visible_terminal_runs"]:
                    if run.Status not in {"Failed", "Cancelled"}:
                        continue
                    rows.append(
                        {
                            "pipeline_name": item["row"].pipeline_name,
                            "cadence": item["row"].cadence,
                            "status": run.Status,
                            "start": run.Start,
                            "error_message": run.ErrorMessage or "No error message",
                        }
                    )
            rows.sort(key=lambda row: row["start"], reverse=True)
            return _query_result(["pipeline_name", "cadence", "status", "start", "error_message"], rows[: plan.limit], plan.visualization)

        if plan.intent == "slowest_pipelines":
            rows = [
                {
                    "pipeline_name": item["row"].pipeline_name,
                    "cadence": item["row"].cadence,
                    "avg_duration_last_7_runs": round(item["row"].average_duration_last_7_runs or 0, 1),
                    "avg_duration_previous_7_runs": round(item["row"].average_duration_previous_7_runs or 0, 1),
                    "duration_delta_pct": item["row"].duration_delta_pct or 0.0,
                }
                for item in contexts
                if item["row"].average_duration_last_7_runs is not None
            ]
            rows.sort(key=lambda row: row["avg_duration_last_7_runs"], reverse=True)
            return _query_result(
                ["pipeline_name", "cadence", "avg_duration_last_7_runs", "avg_duration_previous_7_runs", "duration_delta_pct"],
                rows[: plan.limit],
                plan.visualization,
            )

        if plan.intent == "pipelines_with_retries":
            rows = []
            for item in contexts:
                retry_runs = [run for run in item["retry_runs"] if self._within_window(run.Start, now, plan.time_window_days)]
                if not retry_runs:
                    continue
                rows.append(
                    {
                        "pipeline_name": item["row"].pipeline_name,
                        "cadence": item["row"].cadence,
                        "retry_count": len(retry_runs),
                        "last_retry_at": retry_runs[0].Start,
                    }
                )
            rows.sort(key=lambda row: row["retry_count"], reverse=True)
            return _query_result(["pipeline_name", "cadence", "retry_count", "last_retry_at"], rows[: plan.limit], plan.visualization)

        if plan.intent == "last_run_status":
            rows = [
                {
                    "pipeline_name": item["row"].pipeline_name,
                    "cadence": item["row"].cadence,
                    "last_run_status": item["row"].last_run_status,
                    "last_run_start": item["row"].last_run_start,
                    "last_run_duration_seconds": item["row"].last_run_duration_seconds,
                    "attention_reason": item["row"].attention_reason,
                }
                for item in contexts
            ]
            rows.sort(key=lambda row: row["last_run_start"] or "", reverse=True)
            return _query_result(
                ["pipeline_name", "cadence", "last_run_status", "last_run_start", "last_run_duration_seconds", "attention_reason"],
                rows[: plan.limit],
                plan.visualization,
            )

        rows = [
            {
                "pipeline_name": item["row"].pipeline_name,
                "cadence": item["row"].cadence,
                "last_run_status": item["row"].last_run_status,
                "attention_reason": item["row"].attention_reason,
            }
            for item in contexts
        ]
        return _query_result(["pipeline_name", "cadence", "last_run_status", "attention_reason"], rows[: plan.limit], plan.visualization)

    def _fallback_dashboard_summary(
        self,
        summary: ObservabilitySummaryResponse,
        groups: List[ObservabilityCadenceGroup],
    ) -> ObservabilitySummaryAIResponse:
        metrics = {item.label: item.value for item in summary.summary_metrics}
        attention_titles = ", ".join(item.pipeline_name for item in summary.attention_items[:3]) or "no urgent pipelines"
        group_breakdown = ", ".join(f"{group.label}: {group.attention_count} attention" for group in groups)
        return ObservabilitySummaryAIResponse(
            title="Operational Snapshot",
            summary=(
                f"{metrics.get('Pipelines Needing Attention', '0')} pipelines need attention across the current view, "
                f"with a {metrics.get('Success Rate', '100%')} success rate in the visible window."
            ),
            insights=[
                f"Primary attention is concentrated around {attention_titles}.",
                f"Cadence breakdown: {group_breakdown}.",
                f"Average duration delta sits at {metrics.get('Avg Duration Delta', '+0.0%')} versus the recent baseline.",
            ],
            caveat="This summary is generated from the current filtered dashboard state only.",
            used_fallback=True,
        )

    def _fallback_query_summary(
        self,
        question: str,
        result: ObservabilityQueryResult,
        warnings: List[str],
    ) -> Tuple[str, List[str], List[str], List[str]]:
        if not result.rows:
            return (
                f"No rows matched '{question}'.",
                ["Try broadening the time window or removing a filter."],
                warnings or ["The query returned no data for the selected scope."],
                ["Show recent failures across all cadences.", "List the slowest pipelines in the last 30 days."],
            )
        first_row = result.rows[0]
        summary = f"Returned {result.row_count} rows for '{question}'."
        insights = [
            f"Top result: {', '.join(f'{key}={value}' for key, value in first_row.items() if key in list(first_row.keys())[:3])}.",
            f"Results are currently limited to {result.row_count} rows in the selected window.",
        ]
        follow_ups = [
            "Which pipelines have the lowest success rate?",
            "Show the average duration trend by day.",
        ]
        return summary, insights, warnings, follow_ups

    def _build_display_kql(self, plan: ObservabilityQueryPlan) -> str:
        where_clauses = [f"TimeGenerated >= ago({plan.time_window_days}d)"]
        if plan.cadence:
            where_clauses.append(f"// Cadence '{plan.cadence}' is applied in the app metadata layer.")
        if plan.pipeline_name:
            where_clauses.append(f"PipelineName == '{plan.pipeline_name}'")
        where_sql = "\n| where ".join(["ADFPipelineRun"] + where_clauses)
        if plan.intent == "success_rate_by_pipeline":
            return (
                f"{where_sql}\n"
                '| where Status in ("Succeeded", "Failed", "Cancelled")\n'
                '| summarize SuccessRate = round(100.0 * countif(Status == "Succeeded") / count(), 1), CompletedRuns = count() by PipelineName'
            )
        if plan.intent == "run_count_by_cadence":
            return (
                f"{where_sql}\n"
                "| summarize RunCount = count() by PipelineName\n"
                "| order by RunCount desc"
            )
        if plan.intent == "average_duration_trend":
            bin_size = "1d" if "day" in plan.group_by else "7d"
            return (
                f"{where_sql}\n"
                '| where Status in ("Succeeded", "Failed", "Cancelled")\n'
                f"| summarize AvgDurationMinutes = avg(DurationInMs / 60000.0) by bin(Start, {bin_size})"
            )
        if plan.intent == "recent_failures":
            return (
                f"{where_sql}\n"
                '| where Status in ("Failed", "Cancelled")\n'
                "| project PipelineName, Status, Start, ErrorMessage\n"
                "| order by Start desc"
            )
        if plan.intent == "slowest_pipelines":
            return (
                f"{where_sql}\n"
                '| where Status == "Succeeded"\n'
                "| summarize AvgDurationMinutes = avg(DurationInMs / 60000.0) by PipelineName\n"
                "| order by AvgDurationMinutes desc"
            )
        if plan.intent == "pipelines_with_retries":
            return (
                f"{where_sql}\n"
                "| where RetryAttempt > 0\n"
                "| summarize RetryCount = count(), LatestRetry = max(Start) by PipelineName\n"
                "| order by RetryCount desc"
            )
        if plan.intent == "last_run_status":
            return (
                f"{where_sql}\n"
                "| summarize arg_max(Start, *) by PipelineName\n"
                "| project PipelineName, Status, Start, DurationInMs"
            )
        return f"{where_sql}\n| summarize Count = count() by PipelineName"

    def _extract_pipeline_name(self, question: str) -> Optional[str]:
        data = self.provider.load()
        for metadata in data["metadata"]:
            if metadata.pipeline_name.lower() in question.lower():
                return metadata.pipeline_name
        return None

    def _derive_attention_state(
        self,
        last_status: str,
        stale: bool,
        slowdown: bool,
        recovered: bool,
    ) -> Tuple[AttentionState, str]:
        if last_status in {"Failed", "Cancelled"}:
            return "attention", "Failed in last run"
        if stale:
            return "attention", "Missed expected schedule"
        if slowdown:
            return "watch", "Running slower than baseline"
        if recovered:
            return "recovered", "Recovered after recent failures"
        return "healthy", "Healthy"

    def _matches_filters(
        self,
        metadata: ObservabilityPipelineMetadata,
        row: ObservabilityPipelineRow,
        filters: ObservabilityFilters,
    ) -> bool:
        if filters.cadence and row.cadence != filters.cadence:
            return False
        if filters.status and row.last_run_status != filters.status:
            return False
        if filters.owner and metadata.owner != filters.owner:
            return False
        if filters.criticality and metadata.criticality != filters.criticality:
            return False
        if filters.search and filters.search.lower() not in row.pipeline_name.lower():
            return False
        return True

    def _within_window(self, start_value: str, now: datetime, window_days: int) -> bool:
        return _parse_iso(start_value) >= now - timedelta(days=window_days)


def _query_result(columns: List[str], rows: List[dict], visualization: Optional[str]) -> ObservabilityQueryResult:
    return ObservabilityQueryResult(columns=columns, rows=rows, row_count=len(rows), visualization=visualization)


def _model_copy(model, update: dict):
    if hasattr(model, "model_copy"):
        return model.model_copy(update=update)
    return model.copy(update=update)


def _average_duration(runs: List[AdfPipelineRunRecord]) -> Optional[float]:
    durations = [run.DurationInMs / 1000 for run in runs if run.DurationInMs]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def _average_activity_duration(records: List[AdfActivityRunRecord]) -> Optional[float]:
    durations = [record.DurationInMs / 1000 for record in records if record.DurationInMs]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def _duration_seconds(duration_ms: Optional[int]) -> Optional[int]:
    if duration_ms is None:
        return None
    return int(duration_ms / 1000)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
