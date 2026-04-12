from typing import List, Literal, Optional

from pydantic import BaseModel, Field


IssueClassification = Literal["infra_issue", "data_table_issue", "unknown_issue"]
RoutingTeam = Literal["infra_team", "data_team", "triage_team"]
ScriptRole = Literal["old", "new"]
ServiceStatus = Literal["pending", "running", "completed", "skipped", "failed"]


class System1Request(BaseModel):
    raw_title: str = Field(..., min_length=3)


class System1Result(BaseModel):
    raw_title: str
    division: str
    table_name: str
    issue: str
    mentioned_columns: List[str] = Field(default_factory=list)
    issue_classification: IssueClassification
    routing_team: RoutingTeam
    confidence: float = 0.0
    parsing_notes: List[str] = Field(default_factory=list)


class System2Request(BaseModel):
    division: str
    table_name: str
    issue: str
    mentioned_columns: List[str] = Field(default_factory=list)


class ColumnMappingRecord(BaseModel):
    old_system: str
    new_system: str
    old_table_name: str
    new_table_name: str
    old_column_name: str
    new_column_name: str
    data_type_old: str
    data_type_new: str
    mapping_status: str = "renamed"
    remarks: str = ""


class ResolvedMetadata(BaseModel):
    division: str
    table_name: str
    old_target_table_name: str
    new_target_table_name: str
    source_tables: List[str] = Field(default_factory=list)
    old_transformation_script_path: str
    new_transformation_script_path: str
    owner_users: List[str] = Field(default_factory=list)
    support_team: str
    business_description: str
    criticality: str
    column_mapping: List[ColumnMappingRecord] = Field(default_factory=list)
    full_column_mapping: List[ColumnMappingRecord] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    reason: str


class ScriptAnalysisRequest(BaseModel):
    system1: System1Result
    system2: ResolvedMetadata
    script_role: ScriptRole


class ScriptAnalysis(BaseModel):
    script_role: ScriptRole
    script_path: str
    issue_focus: str
    summary: str
    prompt_version: Optional[str] = None
    decision: Optional[str] = None
    relevant_columns: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    suspected_causes: List[str] = Field(default_factory=list)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    analysis_warnings: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class SqlQueryResult(BaseModel):
    label: str
    sql: str
    columns: List[str] = Field(default_factory=list)
    rows: List[dict] = Field(default_factory=list)
    row_count: int = 0


class SqlDiagnostic(BaseModel):
    name: str
    purpose: str
    query: SqlQueryResult
    findings: List[str] = Field(default_factory=list)


class IncidentAnalysisRequest(BaseModel):
    system1: System1Result
    system2: ResolvedMetadata


class CompareAnalysesRequest(BaseModel):
    system1: System1Result
    system2: ResolvedMetadata
    old_analysis: ScriptAnalysis
    new_analysis: ScriptAnalysis


class System3Result(BaseModel):
    system1: System1Result
    system2: ResolvedMetadata
    old_analysis: ScriptAnalysis
    new_analysis: ScriptAnalysis
    prompt_version: Optional[str] = None
    decision: Optional[str] = None
    root_cause_family: Optional[str] = None
    issue_impact: str
    old_script_observation: str
    new_script_observation: str
    likely_root_cause: str
    possible_resolutions: List[str] = Field(default_factory=list)
    recommended_next_step: str
    final_summary: str
    evidence_gaps: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    analysis_warnings: List[str] = Field(default_factory=list)


class System4Request(BaseModel):
    system1: System1Result
    system2: ResolvedMetadata
    new_analysis: ScriptAnalysis


class System4Result(BaseModel):
    scenario_id: Optional[str] = None
    scenario_type: Optional[str] = None
    target_table: str
    primary_query: SqlQueryResult
    diagnostic_queries: List[SqlDiagnostic] = Field(default_factory=list)
    issue_findings: List[str] = Field(default_factory=list)
    summary: str
    explanation_points: List[str] = Field(default_factory=list)
    affected_code_refs: List[EvidenceRef] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class ServiceStep(BaseModel):
    name: str
    status: ServiceStatus
    detail: str


class ChatInvestigateRequest(BaseModel):
    raw_title: str


class ChatInvestigateResponse(BaseModel):
    request_id: str
    routing_team: str
    system1: System1Result
    system2: Optional[ResolvedMetadata] = None
    system3: Optional[System3Result] = None
    system4: Optional[System4Result] = None
    final_summary: str
    markdown_summary: str
    steps: List[ServiceStep] = Field(default_factory=list)
