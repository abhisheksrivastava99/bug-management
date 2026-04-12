from typing import Dict

from bug_management_shared.models import System4Request, System4Result


PROMPT_VERSION = "system4.v1"


def build_system4_prompt(payload: System4Request, heuristic: System4Result) -> Dict[str, str]:
    mapping_rows = "\n".join(
        f"- {row.old_column_name} -> {row.new_column_name}"
        for row in payload.system2.column_mapping
    ) or "- none"
    evidence_rows = []
    for index, evidence in enumerate(payload.new_analysis.evidence[:6]):
        evidence_rows.append(
            f"[{index}] {evidence.file_path}:{evidence.start_line}-{evidence.end_line} | {evidence.reason}\n{evidence.snippet}"
        )
    evidence_text = "\n\n".join(evidence_rows) if evidence_rows else "- none"
    diagnostic_summaries = "\n".join(
        f"- {item.name}: {' | '.join(item.findings) if item.findings else 'No direct finding'}"
        for item in heuristic.diagnostic_queries
    ) or "- none"
    system_prompt = (
        f"You are the SQL versus script comparison prompt in {PROMPT_VERSION}. "
        "Compare deterministic SQLite findings with the provided new-script analysis only. "
        "Do not invent data, code references, or runtime behavior beyond the supplied evidence. "
        "When selecting affected script references, use only the indexed evidence items that were provided."
    )
    user_prompt = f"""
## Incident Context
- Raw title: {payload.system1.raw_title}
- Division: {payload.system1.division}
- Table: {payload.system1.table_name}
- Issue: {payload.system1.issue}
- Mentioned columns: {", ".join(payload.system1.mentioned_columns) or "none"}

## Target Metadata
- Current target table: {payload.system2.new_target_table_name}
- Column mapping:
{mapping_rows}

## Deterministic SQL Findings
- Scenario type: {heuristic.scenario_type or "unmatched"}
- Primary query: {heuristic.primary_query.sql}
- Primary row count: {heuristic.primary_query.row_count}
- Issue findings:
{chr(10).join(f"- {item}" for item in heuristic.issue_findings) if heuristic.issue_findings else "- none"}
- Diagnostic summaries:
{diagnostic_summaries}

## New Script Analysis
- Summary: {payload.new_analysis.summary}
- Decision: {payload.new_analysis.decision or "unknown"}
- Observations: {" | ".join(payload.new_analysis.observations) if payload.new_analysis.observations else "none"}
- Suspected causes: {" | ".join(payload.new_analysis.suspected_causes) if payload.new_analysis.suspected_causes else "none"}

## Indexed New-Script Evidence
{evidence_text}

## Required Reasoning Tasks
1. Explain how the deterministic SQL state aligns or conflicts with the new-script behavior.
2. Mention the specific SQL symptom, such as missing rows, duplicate rows, invalid values, null spikes, or filter loss.
3. Choose only from the indexed evidence items when citing affected code references.
4. Keep the explanation grounded and concise.

## Output JSON Schema
Return a JSON object with exactly these keys:
- summary: string
- explanation_points: array of strings
- affected_evidence_indexes: array of integers
- confidence: number between 0 and 1
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}
