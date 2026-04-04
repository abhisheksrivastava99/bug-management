from typing import Dict

from bug_management_shared.models import CompareAnalysesRequest, ScriptAnalysis, ScriptAnalysisRequest


PROMPT_VERSION = "system3.v4"


def build_script_analysis_prompt(
    payload: ScriptAnalysisRequest,
    heuristic: ScriptAnalysis,
) -> Dict[str, str]:
    evidence_text = _format_evidence_with_snippets(heuristic)
    metadata_text = _format_metadata(payload)
    role_focus = ", ".join(heuristic.relevant_columns) or "none"
    counterpart_focus = _counterpart_focus(payload, payload.script_role)
    system_prompt = (
        f"You are the {payload.script_role}_script_analysis prompt in {PROMPT_VERSION}. "
        "Analyze exactly one PySpark script using only the supplied metadata and evidence. "
        "The column mapping table is the canonical translation layer between Gavin2 legacy names and Gavin3 business names. "
        "Treat every mapping row as a renamed Gavin2-to-Gavin3 relationship, even if the workbook itself does not store a mapping_status column. "
        "Literal name equality across old and new scripts is not expected. "
        "If evidence is weak, say so explicitly instead of guessing."
    )
    user_prompt = f"""
## Prompt Family
{payload.script_role}_script_analysis

## Incident Context
- Raw title: {payload.system1.raw_title}
- Division: {payload.system1.division}
- Table: {payload.system1.table_name}
- Issue: {payload.system1.issue}
- Mentioned issue columns: {", ".join(payload.system1.mentioned_columns) or "none"}

## Role-Specific Focus
- Script role: {payload.script_role}
- Analyze these names in this script: {role_focus}
- Related names in the opposite script: {counterpart_focus}

## Resolved Metadata
{metadata_text}

## Focused Evidence
{evidence_text}

## Required Reasoning Tasks
1. Describe how this single script treats the mapped issue-related columns or output fields.
2. For an old script, reason in Gavin2 legacy names. For a new script, reason in Gavin3 business names.
3. Identify whether the mapped field is selected, derived, renamed incorrectly, filtered, join-affected, or absent from the shown evidence.
4. Call out evidence gaps and unresolved questions when the excerpt is insufficient.

## Allowed Conclusions
- supported
- partially_supported
- insufficient_evidence

## Forbidden Speculation
- Do not infer hidden code, runtime behavior, or owner clarifications that are not shown.
- Do not assume the same literal column name should exist in both scripts.
- Do not claim end-to-end root cause across old and new scripts here.

## Output JSON Schema
Return a JSON object with exactly these keys:
- prompt_version: string
- decision: string
- summary: string
- observations: array of strings
- suspected_causes: array of strings
- evidence_gaps: array of strings
- unresolved_questions: array of strings
- analysis_warnings: array of strings
- confidence: number between 0 and 1
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def build_synthesis_prompt(payload: CompareAnalysesRequest) -> Dict[str, str]:
    old_analysis = _format_analysis_summary(payload.old_analysis)
    new_analysis = _format_analysis_summary(payload.new_analysis)
    mapping_rows = "\n".join(
        f"- {row.old_column_name} -> {row.new_column_name}"
        for row in payload.system2.column_mapping
    ) or "- none"
    system_prompt = (
        f"You are the analysis_synthesis prompt in {PROMPT_VERSION}. "
        "Compare only the structured old/new analysis outputs plus the column mapping metadata. "
        "The mapping is the canonical bridge between legacy Gavin2 names and Gavin3 names. "
        "Treat every mapping row as a rename, even when the source workbook omits an explicit mapping_status column. "
        "Do not inspect raw script text and do not expect literal name equality between scripts."
    )
    user_prompt = f"""
## Prompt Family
analysis_synthesis

## Incident Context
- Raw title: {payload.system1.raw_title}
- Division: {payload.system1.division}
- Table: {payload.system1.table_name}
- Issue: {payload.system1.issue}

## Metadata Summary
- Old target table: {payload.system2.old_target_table_name}
- New target table: {payload.system2.new_target_table_name}
- Source tables: {", ".join(payload.system2.source_tables)}
- Support team: {payload.system2.support_team}
- Column mapping:
{mapping_rows}

## Old Analysis Summary
{old_analysis}

## New Analysis Summary
{new_analysis}

## Required Reasoning Tasks
1. Compare old legacy behavior to mapped Gavin3 behavior using the column mapping as the translation layer.
2. Choose the most likely regression family from the allowed families below.
3. Decide whether the evidence supports a regression, a join/filter investigation, an upstream-source investigation, or insufficient evidence.
4. Produce a concise explanation and action-oriented next steps that explicitly mention the relevant old -> new mapping.

## Allowed Decisions
- regression_detected
- investigate_join_logic
- investigate_filter_logic
- upstream_source_check_required
- insufficient_evidence

## Allowed Root Cause Families
- missing_final_select
- alias_mismatch
- renamed_derivation
- join_null_spike
- filter_row_loss
- source_column_disappearance
- insufficient_evidence

## Forbidden Speculation
- Do not cite raw script text.
- Do not invent new mappings, owner clarifications, or runtime facts not present in metadata or analysis outputs.
- Do not overstate confidence when evidence gaps remain.

## Output JSON Schema
Return a JSON object with exactly these keys:
- prompt_version: string
- decision: string
- root_cause_family: string
- issue_impact: string
- old_script_observation: string
- new_script_observation: string
- likely_root_cause: string
- possible_resolutions: array of strings
- recommended_next_step: string
- final_summary: string
- evidence_gaps: array of strings
- unresolved_questions: array of strings
- analysis_warnings: array of strings
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def _format_metadata(payload: ScriptAnalysisRequest) -> str:
    mapping_rows = "\n".join(
        f"- {row.old_column_name} -> {row.new_column_name}"
        for row in payload.system2.column_mapping
    ) or "- none"
    return (
        f"- Old target table: {payload.system2.old_target_table_name}\n"
        f"- New target table: {payload.system2.new_target_table_name}\n"
        f"- Source tables: {', '.join(payload.system2.source_tables)}\n"
        f"- Column mapping is the canonical translation layer.\n"
        f"- Column mapping:\n{mapping_rows}"
    )


def _format_evidence_with_snippets(heuristic: ScriptAnalysis) -> str:
    if not heuristic.evidence:
        return "- No direct evidence snippets were found."
    chunks = []
    for item in heuristic.evidence[:6]:
        chunks.append(
            f"- {item.file_path}:{item.start_line}-{item.end_line} | {item.reason}\n{item.snippet}"
        )
    return "\n\n".join(chunks)


def _format_analysis_summary(analysis: ScriptAnalysis) -> str:
    lines = [
        f"- Script role: {analysis.script_role}",
        f"- Summary: {analysis.summary}",
        f"- Decision: {analysis.decision or 'unknown'}",
        f"- Observations: {' | '.join(analysis.observations) if analysis.observations else 'none'}",
        f"- Suspected causes: {' | '.join(analysis.suspected_causes) if analysis.suspected_causes else 'none'}",
        f"- Evidence gaps: {' | '.join(analysis.evidence_gaps) if analysis.evidence_gaps else 'none'}",
        f"- Unresolved questions: {' | '.join(analysis.unresolved_questions) if analysis.unresolved_questions else 'none'}",
        f"- Warnings: {' | '.join(analysis.analysis_warnings) if analysis.analysis_warnings else 'none'}",
    ]
    return "\n".join(lines)


def _counterpart_focus(payload: ScriptAnalysisRequest, script_role: str) -> str:
    if script_role == "old":
        names = [row.new_column_name for row in payload.system2.column_mapping if row.new_column_name]
    else:
        names = [row.old_column_name for row in payload.system2.column_mapping if row.old_column_name]
    return ", ".join(names) if names else "none"
