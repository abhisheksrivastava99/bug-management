from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ObservabilityCadence = Literal["daily", "weekly", "monthly"]
ObservabilityStatus = Literal["Succeeded", "Failed", "Cancelled", "InProgress"]
AttentionState = Literal["healthy", "watch", "attention", "recovered"]
QueryIntent = Literal[
    "success_rate_by_pipeline",
    "run_count_by_cadence",
    "average_duration_trend",
    "recent_failures",
    "slowest_pipelines",
    "pipelines_with_retries",
    "last_run_status",
    "unsupported",
]


class ObservabilityPipelineMetadata(BaseModel):
    pipeline_name: str
    pipeline_id: str
    cadence: ObservabilityCadence
    owner: str
    criticality: str
    business_domain: str
    schedule_timezone: str
    schedule_time: str
    day_of_week: Optional[str] = None
    day_of_month: Optional[int] = None
    scenario_profile: str
    trigger_name: str
    trigger_type: str = "Schedule"
    resource_id: str


class AdfTriggerRunRecord(BaseModel):
    TimeGenerated: str
    TriggerRunId: str
    TriggerName: str
    TriggerType: str
    Status: ObservabilityStatus
    Start: str
    End: Optional[str] = None
    PipelineName: str
    CorrelationId: str
    RetryAttempt: int = 0
    ResourceId: str


class AdfPipelineRunRecord(BaseModel):
    TimeGenerated: str
    RunId: str
    PipelineName: str
    Status: ObservabilityStatus
    Start: str
    End: Optional[str] = None
    DurationInMs: Optional[int] = None
    FailureType: Optional[str] = None
    ErrorMessage: Optional[str] = None
    CorrelationId: str
    TriggerRunId: Optional[str] = None
    TriggerType: str = "Schedule"
    RetryAttempt: int = 0
    ResourceId: str


class AdfActivityRunRecord(BaseModel):
    TimeGenerated: str
    ActivityRunId: str
    RunId: str
    ActivityName: str
    ActivityType: str
    Status: ObservabilityStatus
    Start: str
    End: Optional[str] = None
    DurationInMs: Optional[int] = None
    ErrorMessage: Optional[str] = None
    RetryAttempt: int = 0
    ResourceId: str


class ObservabilityFilters(BaseModel):
    window_days: int = 30
    cadence: Optional[ObservabilityCadence] = None
    status: Optional[ObservabilityStatus] = None
    owner: Optional[str] = None
    criticality: Optional[str] = None
    search: Optional[str] = None


class ObservabilitySummaryMetric(BaseModel):
    label: str
    value: str
    raw_value: Optional[float] = None
    tone: Literal["neutral", "warning", "positive"] = "neutral"


class ObservabilityAttentionItem(BaseModel):
    kind: str
    pipeline_name: str
    cadence: ObservabilityCadence
    title: str
    description: str
    status: ObservabilityStatus
    attention_state: AttentionState


class ObservabilityFailureEvent(BaseModel):
    pipeline_name: str
    cadence: ObservabilityCadence
    status: ObservabilityStatus
    started_at: str
    error_message: Optional[str] = None


class ObservabilityPipelineRow(BaseModel):
    pipeline_name: str
    cadence: ObservabilityCadence
    owner: str
    criticality: str
    business_domain: str
    scenario_profile: str
    last_run_status: ObservabilityStatus
    last_run_start: Optional[str] = None
    last_run_end: Optional[str] = None
    last_run_duration_seconds: Optional[int] = None
    average_duration_last_7_runs: Optional[float] = None
    average_duration_previous_7_runs: Optional[float] = None
    duration_delta_pct: Optional[float] = None
    success_rate_window: float = 0.0
    failure_count_window: int = 0
    latest_error_message: Optional[str] = None
    stale: bool = False
    recovered_after_failure: bool = False
    attention_state: AttentionState = "healthy"
    attention_reason: str = "Healthy"


class ObservabilityCadenceGroup(BaseModel):
    cadence: ObservabilityCadence
    label: str
    total_count: int
    attention_count: int
    pipelines: List[ObservabilityPipelineRow] = Field(default_factory=list)


class ObservabilitySummaryResponse(BaseModel):
    generated_at: str
    filters: ObservabilityFilters
    summary_metrics: List[ObservabilitySummaryMetric] = Field(default_factory=list)
    attention_items: List[ObservabilityAttentionItem] = Field(default_factory=list)
    top_regressions: List[ObservabilityPipelineRow] = Field(default_factory=list)
    recent_failures: List[ObservabilityFailureEvent] = Field(default_factory=list)


class ObservabilityPipelinesResponse(BaseModel):
    generated_at: str
    filters: ObservabilityFilters
    total_pipeline_count: int
    filtered_pipeline_count: int
    groups: List[ObservabilityCadenceGroup] = Field(default_factory=list)


class ObservabilityRunHistoryItem(BaseModel):
    run_id: str
    trigger_type: str
    status: ObservabilityStatus
    start: str
    end: Optional[str] = None
    duration_seconds: Optional[int] = None
    retry_attempt: int = 0
    error_message: Optional[str] = None
    is_scheduled: bool = True


class ObservabilityTrendPoint(BaseModel):
    label: str
    start: str
    duration_seconds: Optional[int] = None
    status: ObservabilityStatus


class ObservabilityRetrySummary(BaseModel):
    total_retries: int = 0
    latest_retry_at: Optional[str] = None
    recent_retry_runs: List[ObservabilityRunHistoryItem] = Field(default_factory=list)


class ObservabilityActivitySummaryItem(BaseModel):
    activity_name: str
    activity_type: str
    latest_status: ObservabilityStatus
    average_duration_seconds: Optional[float] = None
    runs_seen: int = 0
    failure_count: int = 0


class ObservabilityPipelineDetailResponse(BaseModel):
    generated_at: str
    filters: ObservabilityFilters
    pipeline: ObservabilityPipelineRow
    attention_items: List[ObservabilityAttentionItem] = Field(default_factory=list)
    run_history: List[ObservabilityRunHistoryItem] = Field(default_factory=list)
    duration_trend: List[ObservabilityTrendPoint] = Field(default_factory=list)
    latest_failure: Optional[ObservabilityRunHistoryItem] = None
    retry_summary: ObservabilityRetrySummary = Field(default_factory=ObservabilityRetrySummary)
    activity_summary: List[ObservabilityActivitySummaryItem] = Field(default_factory=list)


class ObservabilitySummaryAIRequest(BaseModel):
    summary: ObservabilitySummaryResponse
    groups: List[ObservabilityCadenceGroup] = Field(default_factory=list)


class ObservabilitySummaryAIResponse(BaseModel):
    title: str
    summary: str
    insights: List[str] = Field(default_factory=list)
    caveat: Optional[str] = None
    used_fallback: bool = False


class ObservabilityQueryPlan(BaseModel):
    intent: QueryIntent
    dataset: str
    metric: str
    time_window_days: int = 30
    cadence: Optional[ObservabilityCadence] = None
    pipeline_name: Optional[str] = None
    group_by: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_field: Optional[str] = None
    sort_direction: Literal["asc", "desc"] = "desc"
    limit: int = 10
    visualization: Optional[str] = None


class ObservabilityQueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    visualization: Optional[str] = None


class ObservabilityQueryRequest(BaseModel):
    question: str
    filters: ObservabilityFilters = Field(default_factory=ObservabilityFilters)


class ObservabilityQueryResponse(BaseModel):
    question: str
    display_kql: str
    query_plan: ObservabilityQueryPlan
    result: ObservabilityQueryResult
    summary: str
    insights: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    used_fallback: bool = False
