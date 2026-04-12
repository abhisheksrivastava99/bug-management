import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .config import CATALOG_ROOT, SQLITE_ROOT
from .llm import OpenAIChatClient
from .models import EvidenceRef, SqlDiagnostic, SqlQueryResult, System4Request, System4Result
from .system4_prompt_pack import PROMPT_VERSION, build_system4_prompt
from .text_utils import dedupe, normalize_key


LLM_CLIENT = OpenAIChatClient()
CATALOG_PATH = Path(os.getenv("BM_SCENARIO_CATALOG_JSON", CATALOG_ROOT / "scenario_catalog.json"))
SQLITE_PATH = Path(os.getenv("BM_SQLITE_PATH", SQLITE_ROOT / "bug_management_demo.db"))
MAX_RESULT_ROWS = 25


async def analyze_system4(payload: System4Request) -> System4Result:
    target_table = payload.system2.new_target_table_name
    scenario = _match_scenario(payload)
    if not SQLITE_PATH.exists():
        return _warning_result(
            target_table=target_table,
            warnings=[f"SQLite fixture not found at {SQLITE_PATH}."],
        )
    if not scenario:
        return _warning_result(
            target_table=target_table,
            warnings=[
                "No deterministic SQLite scenario matched the current Jira title or issue metadata.",
            ],
        )

    primary_query, diagnostics, issue_findings, warnings = _run_sql_diagnostics(payload, scenario)
    affected_refs = _select_affected_code_refs(payload.new_analysis.evidence, scenario, issue_findings)
    summary = _build_summary(target_table, scenario, issue_findings, payload.new_analysis.summary)
    explanation_points = _build_explanation_points(issue_findings, payload.new_analysis.observations)
    heuristic = System4Result(
        scenario_id=scenario.get("id"),
        scenario_type=scenario.get("scenario_type"),
        target_table=target_table,
        primary_query=primary_query,
        diagnostic_queries=diagnostics,
        issue_findings=issue_findings,
        summary=summary,
        explanation_points=explanation_points,
        affected_code_refs=affected_refs,
        warnings=warnings,
        confidence=_heuristic_confidence(issue_findings, affected_refs),
    )
    return await _maybe_llm_compare(payload, heuristic)


def _warning_result(target_table: str, warnings: List[str]) -> System4Result:
    return System4Result(
        target_table=target_table,
        primary_query=SqlQueryResult(label="Issue rows", sql="", columns=[], rows=[], row_count=0),
        summary=f"System 4 could not produce SQL diagnostics for {target_table}.",
        explanation_points=[],
        warnings=warnings,
        confidence=0.0,
    )


def _run_sql_diagnostics(
    payload: System4Request,
    scenario: Dict,
) -> tuple[SqlQueryResult, List[SqlDiagnostic], List[str], List[str]]:
    sql_fixture = scenario["sql_fixture"]
    target_table = payload.system2.new_target_table_name
    focus_column = sql_fixture.get("diagnostic_hints", {}).get("focus_column")
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    diagnostics: List[SqlDiagnostic] = []
    findings: List[str] = []
    warnings: List[str] = []

    with sqlite3.connect(SQLITE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        target_columns = _table_columns(connection, target_table)
        schema_query = _run_query(
            connection,
            label="Target schema",
            sql=f'PRAGMA table_info("{target_table}")',
        )
        diagnostics.append(
            SqlDiagnostic(
                name="Target schema",
                purpose="Show the current SQLite target-table schema before issue-specific checks.",
                query=schema_query,
                findings=[],
            )
        )

        primary_query = _issue_rows_query(connection, target_table, issue_key_column, issue_key_values)

        if focus_column and focus_column not in target_columns:
            findings.append(f"{focus_column} is not present in the current target-table schema.")

        scenario_type = scenario.get("scenario_type", "")
        if scenario_type == "missing_final_select":
            diagnostics.extend(
                _missing_final_select_diagnostics(connection, target_table, sql_fixture, target_columns, findings)
            )
        elif scenario_type == "alias_mismatch":
            diagnostics.extend(_alias_mismatch_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "renamed_derivation":
            diagnostics.extend(_alias_mismatch_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "join_null_spike":
            diagnostics.extend(_join_null_spike_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "filter_row_loss":
            diagnostics.extend(_filter_row_loss_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "source_column_disappearance":
            diagnostics.extend(
                _missing_final_select_diagnostics(connection, target_table, sql_fixture, target_columns, findings)
            )
        elif scenario_type == "duplicate_data":
            diagnostics.extend(_duplicate_data_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "invalid_type_format":
            diagnostics.extend(_invalid_type_diagnostics(connection, target_table, sql_fixture, findings))
        elif scenario_type == "join_filter_miss":
            diagnostics.extend(_join_filter_miss_diagnostics(connection, target_table, sql_fixture, findings))
        else:
            findings.append("The SQL state is present, but there is not enough deterministic evidence to isolate the issue.")

        if not findings:
            warnings.extend(sql_fixture.get("expected_findings", []))
        else:
            findings = dedupe(findings)
        return primary_query, diagnostics, findings, warnings


def _missing_final_select_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    target_columns: List[str],
    findings: List[str],
) -> List[SqlDiagnostic]:
    diagnostics: List[SqlDiagnostic] = []
    support_table = sql_fixture["diagnostic_hints"]["support_lookup_table"]
    support_focus_column = sql_fixture["diagnostic_hints"]["support_focus_column"]
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    support_query = _issue_rows_query(connection, support_table, issue_key_column, issue_key_values)
    local_findings = []
    if support_query.row_count:
        local_findings.append(f"Support table {support_table} still has rows for the issue keys.")
    if support_focus_column not in target_columns:
        local_findings.append(f"{support_focus_column} is missing from {target_table} but still visible in {support_table}.")
    findings.extend(local_findings)
    diagnostics.append(
        SqlDiagnostic(
            name="Support rows",
            purpose="Validate whether upstream support rows still carry the issue-related column.",
            query=support_query,
            findings=local_findings,
        )
    )
    return diagnostics


def _alias_mismatch_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    diagnostics: List[SqlDiagnostic] = []
    wrong_column = sql_fixture["diagnostic_hints"].get("wrong_output_column")
    focus_column = sql_fixture["diagnostic_hints"].get("focus_column")
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    target_columns = _table_columns(connection, target_table)
    local_findings = []
    if wrong_column and wrong_column in target_columns:
        display_sql, exec_sql, params = _build_issue_key_query(target_table, issue_key_column, issue_key_values, [issue_key_column, wrong_column])
        wrong_query = _run_query(connection, label="Wrong output column", sql=display_sql, exec_sql=exec_sql, params=params)
        diagnostics.append(
            SqlDiagnostic(
                name="Wrong output column",
                purpose="Show the current target-table values under the unexpected output column.",
                query=wrong_query,
                findings=[],
            )
        )
        local_findings.append(f"Current rows are populated under {wrong_column} instead of {focus_column}.")
    if focus_column and focus_column not in target_columns:
        local_findings.append(f"Mapped column {focus_column} is not available in the target schema.")
    findings.extend(local_findings)
    if not diagnostics:
        diagnostics.append(
            SqlDiagnostic(
                name="Wrong output column",
                purpose="No alternative output column was found in the current target schema.",
                query=SqlQueryResult(label="Wrong output column", sql="", columns=[], rows=[], row_count=0),
                findings=local_findings,
            )
        )
    return diagnostics


def _join_null_spike_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    diagnostics: List[SqlDiagnostic] = []
    focus_column = sql_fixture["diagnostic_hints"]["focus_column"]
    support_table = sql_fixture["diagnostic_hints"]["support_lookup_table"]
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    target_null_sql, target_null_exec, params = _build_issue_key_query(
        target_table,
        issue_key_column,
        issue_key_values,
        ["*"],
        extra_clause=f'AND "{focus_column}" IS NULL',
    )
    null_query = _run_query(connection, label="Null rows", sql=target_null_sql, exec_sql=target_null_exec, params=params)
    support_query = _issue_rows_query(connection, support_table, issue_key_column, issue_key_values)
    local_findings = []
    if null_query.row_count:
        local_findings.append(f"{focus_column} is null in the target table for the issue keys.")
    if support_query.row_count:
        local_findings.append(f"Join-side support rows still exist in {support_table}, which points to a join mismatch instead of missing source data.")
    findings.extend(local_findings)
    diagnostics.extend(
        [
            SqlDiagnostic(
                name="Null spike rows",
                purpose="Show current target-table rows where the focus column is null.",
                query=null_query,
                findings=local_findings[:1],
            ),
            SqlDiagnostic(
                name="Support join rows",
                purpose="Show join-side support rows for the same issue keys.",
                query=support_query,
                findings=local_findings[1:],
            ),
        ]
    )
    return diagnostics


def _filter_row_loss_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    diagnostics: List[SqlDiagnostic] = []
    base_table = sql_fixture["diagnostic_hints"]["join_base_table"]
    support_table = sql_fixture["diagnostic_hints"]["support_lookup_table"]
    filter_column = sql_fixture["diagnostic_hints"]["filter_column"]
    filter_value = sql_fixture["diagnostic_hints"]["filter_value"]
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    base_query = _issue_rows_query(connection, base_table, issue_key_column, issue_key_values)
    support_join_column = sql_fixture["diagnostic_hints"]["support_join_column"]
    filter_sql = (
        f'SELECT base."{issue_key_column}", status."{filter_column}" '
        f'FROM "{base_table}" AS base '
        f'LEFT JOIN "{support_table}" AS status ON base."{support_join_column}" = status."{support_join_column}" '
        f'WHERE base."{issue_key_column}" IN ({_binding_placeholders(issue_key_values)})'
    )
    filter_query = _run_query(connection, label="Filter comparison", sql=filter_sql, params=issue_key_values)
    local_findings = []
    if not _issue_rows_query(connection, target_table, issue_key_column, issue_key_values).row_count:
        local_findings.append(f"The issue key does not appear in {target_table} after the current filter logic.")
    if filter_query.row_count and any(row.get(filter_column) != filter_value for row in filter_query.rows):
        local_findings.append(f"Joined support rows failed the {filter_column} = {filter_value} condition.")
    findings.extend(local_findings)
    diagnostics.extend(
        [
            SqlDiagnostic(
                name="Base input rows",
                purpose="Confirm the issue key exists before the filter is applied.",
                query=base_query,
                findings=[],
            ),
            SqlDiagnostic(
                name="Filter comparison",
                purpose="Show the join-side values that decide whether the row survives the filter.",
                query=filter_query,
                findings=local_findings,
            ),
        ]
    )
    return diagnostics


def _duplicate_data_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    duplicate_key = sql_fixture["diagnostic_hints"]["duplicate_key_column"]
    duplicate_sql = (
        f'SELECT "{duplicate_key}", COUNT(*) AS duplicate_count '
        f'FROM "{target_table}" '
        f'GROUP BY "{duplicate_key}" '
        f'HAVING COUNT(*) > 1'
    )
    grouped_query = _run_query(connection, label="Duplicate key counts", sql=duplicate_sql)
    duplicate_rows_sql = (
        f'SELECT * FROM "{target_table}" '
        f'WHERE "{duplicate_key}" IN (SELECT "{duplicate_key}" FROM "{target_table}" GROUP BY "{duplicate_key}" HAVING COUNT(*) > 1)'
    )
    duplicate_rows = _run_query(connection, label="Duplicate rows", sql=duplicate_rows_sql)
    local_findings = []
    if grouped_query.row_count:
        local_findings.append(f"Duplicate target-table rows were found for {duplicate_key}.")
    findings.extend(local_findings)
    return [
        SqlDiagnostic(
            name="Duplicate key counts",
            purpose="Group rows by the business key to find duplicates.",
            query=grouped_query,
            findings=local_findings,
        ),
        SqlDiagnostic(
            name="Duplicate rows",
            purpose="Show the full duplicated target-table rows.",
            query=duplicate_rows,
            findings=[],
        ),
    ]


def _invalid_type_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    focus_column = sql_fixture["diagnostic_hints"]["focus_column"]
    invalid_sql = (
        f'SELECT * FROM "{target_table}" '
        f'WHERE "{focus_column}" IS NOT NULL AND "{focus_column}" NOT GLOB "????-??-??*"'
    )
    invalid_query = _run_query(connection, label="Invalid timestamp values", sql=invalid_sql)
    local_findings = []
    if invalid_query.row_count:
        local_findings.append(f"{focus_column} contains non-ISO timestamp strings in the current target table.")
    findings.extend(local_findings)
    return [
        SqlDiagnostic(
            name="Invalid timestamp values",
            purpose="Find target-table rows whose timestamp-like value does not match the expected pattern.",
            query=invalid_query,
            findings=local_findings,
        )
    ]


def _join_filter_miss_diagnostics(
    connection: sqlite3.Connection,
    target_table: str,
    sql_fixture: Dict,
    findings: List[str],
) -> List[SqlDiagnostic]:
    diagnostics: List[SqlDiagnostic] = []
    base_table = sql_fixture["diagnostic_hints"]["join_base_table"]
    support_table = sql_fixture["diagnostic_hints"]["support_lookup_table"]
    join_columns = sql_fixture["diagnostic_hints"]["join_columns"]
    filter_column = sql_fixture["diagnostic_hints"]["filter_column"]
    filter_value = sql_fixture["diagnostic_hints"]["filter_value"]
    issue_key_column = sql_fixture["issue_key_column"]
    issue_key_values = sql_fixture["issue_key_values"]
    base_query = _issue_rows_query(connection, base_table, issue_key_column, issue_key_values)
    join_condition = " AND ".join(f'base."{column}" = status."{column}"' for column in join_columns)
    joined_sql = (
        f'SELECT base."{join_columns[0]}", base."{join_columns[1]}", status."{filter_column}" '
        f'FROM "{base_table}" AS base '
        f'LEFT JOIN "{support_table}" AS status ON {join_condition} '
        f'WHERE base."{issue_key_column}" IN ({_binding_placeholders(issue_key_values)})'
    )
    joined_query = _run_query(connection, label="Join-side filter rows", sql=joined_sql, params=issue_key_values)
    target_issue_rows = _issue_rows_query(connection, target_table, issue_key_column, issue_key_values)
    local_findings = []
    if not target_issue_rows.row_count:
        local_findings.append(f"The issue key does not appear in {target_table} after the join and filter.")
    if joined_query.row_count and any(row.get(filter_column) != filter_value for row in joined_query.rows):
        local_findings.append(f"Joined rows fail the {filter_column} = {filter_value} eligibility check.")
    findings.extend(local_findings)
    diagnostics.extend(
        [
            SqlDiagnostic(
                name="Base join rows",
                purpose="Confirm the base table still has the issue key before the join filter.",
                query=base_query,
                findings=[],
            ),
            SqlDiagnostic(
                name="Join-side filter rows",
                purpose="Show the join-side eligibility value for the issue key.",
                query=joined_query,
                findings=local_findings,
            ),
        ]
    )
    return diagnostics


def _issue_rows_query(
    connection: sqlite3.Connection,
    table_name: str,
    issue_key_column: str,
    issue_key_values: Sequence[str],
) -> SqlQueryResult:
    display_sql, exec_sql, params = _build_issue_key_query(table_name, issue_key_column, issue_key_values, ["*"])
    return _run_query(connection, label="Issue rows", sql=display_sql, exec_sql=exec_sql, params=params)


def _build_issue_key_query(
    table_name: str,
    issue_key_column: str,
    issue_key_values: Sequence[str],
    columns: Sequence[str],
    extra_clause: str = "",
) -> tuple[str, str, Sequence[str]]:
    selected_columns = "*" if list(columns) == ["*"] else ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in issue_key_values)
    literal_values = ", ".join(json.dumps(value) for value in issue_key_values)
    exec_sql = (
        f'SELECT {selected_columns} FROM "{table_name}" '
        f'WHERE "{issue_key_column}" IN ({placeholders}) {extra_clause} '
        f'ORDER BY "{issue_key_column}"'
    ).strip()
    display_sql = (
        f'SELECT {selected_columns} FROM "{table_name}" '
        f'WHERE "{issue_key_column}" IN ({literal_values}) {extra_clause} '
        f'ORDER BY "{issue_key_column}"'
    ).strip()
    return display_sql, exec_sql, issue_key_values


def _run_query(
    connection: sqlite3.Connection,
    label: str,
    sql: str,
    exec_sql: Optional[str] = None,
    params: Optional[Sequence] = None,
) -> SqlQueryResult:
    cursor = connection.execute(exec_sql or sql, params or [])
    rows = [dict(row) for row in cursor.fetchall()]
    columns = list(rows[0].keys()) if rows else [item[0] for item in cursor.description or []]
    return SqlQueryResult(
        label=label,
        sql=sql,
        columns=columns,
        rows=rows[:MAX_RESULT_ROWS],
        row_count=len(rows),
    )


def _table_columns(connection: sqlite3.Connection, table_name: str) -> List[str]:
    cursor = connection.execute(f'PRAGMA table_info("{table_name}")')
    return [row["name"] for row in cursor.fetchall()]


def _build_summary(target_table: str, scenario: Dict, issue_findings: List[str], new_analysis_summary: str) -> str:
    if issue_findings:
        return (
            f'System 4 found SQLite evidence for {target_table}: {issue_findings[0]} '
            f'New-script analysis indicates: {new_analysis_summary}'
        )
    return f"System 4 reviewed {target_table}, but the deterministic SQL diagnostics were inconclusive."


def _build_explanation_points(issue_findings: List[str], observations: List[str]) -> List[str]:
    points = list(issue_findings[:3])
    if observations:
        points.append(f"New script observation: {observations[0]}")
    if len(observations) > 1:
        points.append(f"Additional new script signal: {observations[1]}")
    return dedupe(points)


def _select_affected_code_refs(
    evidence: Iterable[EvidenceRef],
    scenario: Dict,
    issue_findings: List[str],
) -> List[EvidenceRef]:
    hints = scenario.get("sql_fixture", {}).get("diagnostic_hints", {})
    candidate_terms = {
        normalize_key(hints.get("focus_column", "")),
        normalize_key(hints.get("wrong_output_column", "")),
        normalize_key(hints.get("filter_column", "")),
    }
    if "join" in " ".join(issue_findings).lower():
        candidate_terms.add("join")
    if "filter" in " ".join(issue_findings).lower():
        candidate_terms.add("filter")

    selected: List[EvidenceRef] = []
    for item in evidence:
        normalized_snippet = normalize_key(item.snippet)
        if any(term and term in normalized_snippet for term in candidate_terms):
            selected.append(item)
        if len(selected) >= 3:
            break
    if not selected:
        return list(evidence)[:2]
    return selected


def _heuristic_confidence(issue_findings: List[str], affected_refs: List[EvidenceRef]) -> float:
    if issue_findings and affected_refs:
        return 0.84
    if issue_findings:
        return 0.68
    return 0.42


async def _maybe_llm_compare(payload: System4Request, heuristic: System4Result) -> System4Result:
    if not LLM_CLIENT.enabled or not heuristic.issue_findings:
        return heuristic
    prompt = build_system4_prompt(payload, heuristic)
    response = await LLM_CLIENT.complete_json(
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        debug_label=PROMPT_VERSION,
    )
    if not response:
        return heuristic
    try:
        indexes = response.get("affected_evidence_indexes", [])
        affected_refs = [
            payload.new_analysis.evidence[index]
            for index in indexes
            if isinstance(index, int) and 0 <= index < len(payload.new_analysis.evidence)
        ]
        if not affected_refs:
            affected_refs = heuristic.affected_code_refs
        return heuristic.model_copy(
            update={
                "summary": response.get("summary", heuristic.summary),
                "explanation_points": response.get("explanation_points", heuristic.explanation_points),
                "affected_code_refs": affected_refs,
                "confidence": float(response.get("confidence", heuristic.confidence)),
            }
        )
    except Exception:
        return heuristic


@lru_cache(maxsize=1)
def _load_catalog() -> Dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _match_scenario(payload: System4Request) -> Optional[Dict]:
    catalog = _load_catalog()
    normalized_title = normalize_key(payload.system1.raw_title)
    exact_match = next(
        (scenario for scenario in catalog["scenarios"] if normalize_key(scenario["issue_title"]) == normalized_title),
        None,
    )
    if exact_match:
        return exact_match

    mentioned = {normalize_key(item) for item in payload.system1.mentioned_columns}
    issue_tokens = {normalize_key(token) for token in payload.system1.issue.split() if token}
    best_score = -1
    best_match = None
    for scenario in catalog["scenarios"]:
        score = 0
        if scenario["table_name"] == payload.system1.table_name:
            score += 3
        scenario_focus = {normalize_key(item) for item in scenario.get("focus_columns", [])}
        score += len(mentioned & scenario_focus) * 2
        scenario_keywords = {normalize_key(item) for item in scenario.get("expected_keywords", [])}
        score += len(issue_tokens & scenario_keywords)
        if score > best_score:
            best_score = score
            best_match = scenario
    if best_score >= 3:
        return best_match
    return None


def _literal_placeholders(values: Sequence[str]) -> str:
    return ", ".join(json.dumps(value) for value in values)


def _binding_placeholders(values: Sequence[str]) -> str:
    return ", ".join("?" for _ in values)
