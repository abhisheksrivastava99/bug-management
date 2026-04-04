import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.llm import OpenAIChatClient
from bug_management_shared.logging_utils import configure_logging
from bug_management_shared.models import (
    CompareAnalysesRequest,
    EvidenceRef,
    IncidentAnalysisRequest,
    ScriptAnalysis,
    ScriptAnalysisRequest,
    System3Result,
)
from bug_management_shared.text_utils import dedupe, normalize_key
try:
    from services.system3.app.prompt_pack import PROMPT_VERSION, build_script_analysis_prompt, build_synthesis_prompt
except ImportError:
    try:
        from app.prompt_pack import PROMPT_VERSION, build_script_analysis_prompt, build_synthesis_prompt
    except ImportError:  # pragma: no cover - supports direct module loading in tests
        from prompt_pack import PROMPT_VERSION, build_script_analysis_prompt, build_synthesis_prompt


configure_logging("system3")
LOGGER = logging.getLogger("system3")
app = FastAPI(title="System 3 - Script Analyzer", version="0.1.0")
LLM_CLIENT = OpenAIChatClient()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "system3"}


@app.get("/ready")
async def ready() -> dict:
    return {
        "status": "ready",
        "service": "system3",
        "llm_enabled": LLM_CLIENT.enabled,
        "prompt_version": PROMPT_VERSION,
    }


@app.post("/analyze-old-script", response_model=ScriptAnalysis)
async def analyze_old_script(payload: ScriptAnalysisRequest) -> ScriptAnalysis:
    return await _analyze_script(payload)


@app.post("/analyze-new-script", response_model=ScriptAnalysis)
async def analyze_new_script(payload: ScriptAnalysisRequest) -> ScriptAnalysis:
    return await _analyze_script(payload)


@app.post("/compare-analyses", response_model=System3Result)
async def compare_analyses(payload: CompareAnalysesRequest) -> System3Result:
    return await _compare(payload)


@app.post("/analyze-incident", response_model=System3Result)
async def analyze_incident(payload: IncidentAnalysisRequest) -> System3Result:
    old_request = ScriptAnalysisRequest(
        system1=payload.system1,
        system2=payload.system2,
        script_role="old",
    )
    new_request = ScriptAnalysisRequest(
        system1=payload.system1,
        system2=payload.system2,
        script_role="new",
    )
    old_analysis, new_analysis = await asyncio.gather(
        _analyze_script(old_request),
        _analyze_script(new_request),
    )
    return await _compare(
        CompareAnalysesRequest(
            system1=payload.system1,
            system2=payload.system2,
            old_analysis=old_analysis,
            new_analysis=new_analysis,
        )
    )


async def _analyze_script(payload: ScriptAnalysisRequest) -> ScriptAnalysis:
    script_path = (
        payload.system2.old_transformation_script_path
        if payload.script_role == "old"
        else payload.system2.new_transformation_script_path
    )
    path = Path(script_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"script not found: {script_path}")

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    relevant_columns = _derive_relevant_columns(payload)
    primary_mapping = _primary_mapping_row(payload.system1.mentioned_columns, payload.system2.column_mapping)
    evidence = _collect_evidence(
        path,
        lines,
        payload.system1.table_name,
        relevant_columns,
        _derive_counterpart_columns(payload),
    )
    observations, suspected_causes = _derive_observations(payload.script_role, lines, relevant_columns)
    summary = _build_summary(
        payload.script_role,
        relevant_columns,
        observations,
        _mapping_phrase(primary_mapping.old_column_name, primary_mapping.new_column_name) if primary_mapping else "",
    )

    heuristic_analysis = ScriptAnalysis(
        script_role=payload.script_role,
        script_path=str(path),
        issue_focus=payload.system1.issue,
        summary=summary,
        prompt_version=PROMPT_VERSION,
        decision=_analysis_decision(observations, suspected_causes, evidence),
        relevant_columns=relevant_columns,
        observations=observations,
        suspected_causes=suspected_causes,
        evidence=evidence,
        evidence_gaps=_derive_evidence_gaps(payload.script_role, evidence, relevant_columns, observations),
        unresolved_questions=_derive_unresolved_questions(payload.script_role, relevant_columns, observations),
        analysis_warnings=_derive_analysis_warnings(payload, observations),
        confidence=0.82 if evidence else 0.58,
    )

    enriched = await _maybe_llm_analyze(payload, heuristic_analysis)
    return enriched or heuristic_analysis


def _derive_relevant_columns(payload: ScriptAnalysisRequest) -> List[str]:
    pairs = _derive_column_pairs(payload.system1.mentioned_columns, payload.system2.column_mapping)
    if payload.script_role == "old":
        cols = [pair["old_name"] for pair in pairs if pair["old_name"]]
    else:
        cols = [pair["new_name"] for pair in pairs if pair["new_name"]]
    if cols:
        return dedupe(cols)
    return dedupe([col for col in payload.system1.mentioned_columns if col and normalize_key(col)])


def _derive_counterpart_columns(payload: ScriptAnalysisRequest) -> List[str]:
    pairs = _derive_column_pairs(payload.system1.mentioned_columns, payload.system2.column_mapping)
    if payload.script_role == "old":
        cols = [pair["new_name"] for pair in pairs if pair["new_name"]]
    else:
        cols = [pair["old_name"] for pair in pairs if pair["old_name"]]
    return dedupe(cols)


def _derive_column_pairs(mentioned_columns: List[str], mapping_rows: List) -> List[dict]:
    mentioned = {normalize_key(item) for item in mentioned_columns}
    prioritized = []
    remaining = []
    for row in mapping_rows:
        pair = {
            "old_name": row.old_column_name,
            "new_name": row.new_column_name,
            "mapping_status": row.mapping_status,
            "remarks": row.remarks,
        }
        old_key = normalize_key(row.old_column_name)
        new_key = normalize_key(row.new_column_name)
        if mentioned and (old_key in mentioned or new_key in mentioned):
            prioritized.append(pair)
        else:
            remaining.append(pair)
    if mentioned and prioritized:
        return prioritized
    return prioritized + remaining


def _collect_evidence(
    path: Path,
    lines: List[str],
    table_name: str,
    relevant_columns: List[str],
    counterpart_columns: List[str],
) -> List[EvidenceRef]:
    patterns = [normalize_key(table_name)] + [
        normalize_key(col) for col in (relevant_columns + counterpart_columns) if col
    ]
    evidence = []
    seen_indexes = set()
    for index, line in enumerate(lines, start=1):
        normalized_line = normalize_key(line)
        if not any(pattern and pattern in normalized_line for pattern in patterns):
            continue
        seen_indexes.add(index)
        start = max(1, index - 1)
        end = min(len(lines), index + 1)
        snippet = "\n".join(lines[start - 1 : end])
        evidence.append(
            EvidenceRef(
                file_path=str(path),
                start_line=start,
                end_line=end,
                snippet=snippet,
                reason="Relevant table or column reference found in script.",
            )
        )
    if len(evidence) < 2:
        operation_terms = ("select(", "withcolumn(", "alias(", "join(", "filter(", ".where(")
        for index, line in enumerate(lines, start=1):
            if index in seen_indexes:
                continue
            lowered = line.lower()
            if not any(term in lowered for term in operation_terms):
                continue
            start = max(1, index - 1)
            end = min(len(lines), index + 1)
            snippet = "\n".join(lines[start - 1 : end])
            evidence.append(
                EvidenceRef(
                    file_path=str(path),
                    start_line=start,
                    end_line=end,
                    snippet=snippet,
                    reason="Fallback transformation evidence collected for mapping-aware analysis.",
                )
            )
            if len(evidence) >= 6:
                break
    return evidence[:8]


def _derive_observations(script_role: str, lines: List[str], relevant_columns: List[str]) -> tuple:
    joined = "\n".join(lines)
    lowered = joined.lower()
    observations = []
    suspected_causes = []
    aliases = re.findall(r'alias\(["\']([^"\']+)["\']\)', joined, flags=re.IGNORECASE)
    alias_keys = {normalize_key(alias) for alias in aliases if alias}

    select_blocks = _extract_call_blocks(joined, "select")
    select_identifiers = []
    for block in select_blocks:
        select_identifiers.extend(re.findall(r'["\']([^"\']+)["\']', block))
    all_identifiers = re.findall(r'["\']([^"\']+)["\']', joined)
    for column in relevant_columns:
        column_lower = column.lower()
        column_key = normalize_key(column)
        seen_in_select = any(_identifier_matches_target(identifier, column_key) for identifier in select_identifiers)
        seen_anywhere = any(_identifier_matches_target(identifier, column_key) for identifier in all_identifiers)
        if seen_in_select:
            observations.append(f"Column {column} appears in a select statement.")
        if f"drop('{column_lower}')" in lowered or f'drop("{column_lower}")' in lowered:
            observations.append(f"Column {column} is explicitly dropped.")
            suspected_causes.append(f"{column} is dropped in the transformation.")
        alias_patterns = [f"alias('{column_lower}')", f'alias("{column_lower}")']
        if any(pattern in lowered for pattern in alias_patterns):
            observations.append(f"Column {column} is created via alias in the transformation.")
        if f"withcolumn('{column_lower}'" in lowered or f'withcolumn("{column_lower}"' in lowered:
            observations.append(f"Column {column} is derived with withColumn().")
        if not seen_anywhere:
            suspected_causes.append(f"{column} is not directly referenced in the visible {script_role} script.")
            if _looks_like_identifier_only_select(joined):
                observations.append(
                    f"The {script_role} script only selects join keys or identifier fields in visible source handoff blocks, not {column}."
                )
            if aliases:
                observations.append(
                    f"The {script_role} script aliases output columns to different target names: {', '.join(aliases[:4])}."
                )
        elif aliases and column_key not in alias_keys:
            observations.append(
                f"The {script_role} script aliases output columns to different target names: {', '.join(aliases[:4])}."
            )

    if "join(" in lowered:
        observations.append("Script contains join logic that could affect row-level completeness.")
    if "filter(" in lowered or ".where(" in lowered:
        observations.append("Script contains filter logic that could remove rows.")

    if not observations:
        observations.append(
            f"No direct references to the key columns were found in the {script_role} script excerpt."
        )
        suspected_causes.append(
            f"The {script_role} script may not propagate the issue-related column into the final output."
        )
    return dedupe(observations), dedupe(suspected_causes)


def _build_summary(script_role: str, relevant_columns: List[str], observations: List[str], mapping_phrase: str) -> str:
    focus = ", ".join(relevant_columns) if relevant_columns else "issue-related columns"
    if mapping_phrase:
        return f"{script_role.capitalize()} script analysis focused on {focus} with mapping {mapping_phrase}. {' '.join(observations[:2])}"
    return f"{script_role.capitalize()} script analysis focused on {focus}. {' '.join(observations[:2])}"


def _analysis_decision(observations: List[str], suspected_causes: List[str], evidence: List[EvidenceRef]) -> str:
    lowered_obs = " ".join(observations).lower()
    lowered_causes = " ".join(suspected_causes).lower()
    if not evidence:
        return "insufficient_evidence"
    if "explicitly dropped" in lowered_obs or "not directly referenced" in lowered_causes:
        return "partially_supported"
    if "appears in a select statement" in lowered_obs or "derived with withcolumn" in lowered_obs:
        return "supported"
    return "partially_supported"


def _derive_evidence_gaps(
    script_role: str,
    evidence: List[EvidenceRef],
    relevant_columns: List[str],
    observations: List[str],
) -> List[str]:
    gaps = []
    lowered_obs = " ".join(observations).lower()
    if not evidence:
        gaps.append(f"No direct {script_role} script evidence was found for the issue-related columns.")
    for column in relevant_columns:
        if column.lower() not in lowered_obs:
            gaps.append(f"Visible evidence does not confirm how {column} is propagated in the {script_role} script.")
    return dedupe(gaps)


def _derive_unresolved_questions(
    script_role: str,
    relevant_columns: List[str],
    observations: List[str],
) -> List[str]:
    questions = []
    lowered_obs = " ".join(observations).lower()
    if "join logic" in lowered_obs:
        questions.append(f"Does the {script_role} join cardinality change nullability or row completeness?")
    if "filter logic" in lowered_obs:
        questions.append(f"Is the {script_role} filter intentionally narrowing the output?")
    for column in relevant_columns:
        if column.lower() not in lowered_obs:
            questions.append(f"Where should {column} be sourced or derived in the {script_role} pipeline?")
    return dedupe(questions)


def _derive_analysis_warnings(payload: ScriptAnalysisRequest, observations: List[str]) -> List[str]:
    warnings = []
    lowered_obs = " ".join(observations).lower()
    if not payload.system2.column_mapping:
        warnings.append("No column mapping rows were provided for the issue focus.")
    if any(row.mapping_status != "renamed" for row in payload.system2.column_mapping):
        warnings.append("Fixture expected renamed-only mappings, but other mapping statuses were found.")
    if "join logic" in lowered_obs and "filter logic" in lowered_obs:
        warnings.append("Both join and filter behavior may influence the observed issue.")
    return warnings


async def _maybe_llm_analyze(
    payload: ScriptAnalysisRequest,
    heuristic: ScriptAnalysis,
) -> ScriptAnalysis:
    if not LLM_CLIENT.enabled:
        return heuristic
    prompt = build_script_analysis_prompt(payload, heuristic)
    response = await LLM_CLIENT.complete_json(
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        debug_label=f"{payload.script_role}_script_analysis",
    )
    if not response:
        return heuristic
    try:
        return heuristic.model_copy(
            update={
                "prompt_version": response.get("prompt_version", PROMPT_VERSION),
                "decision": response.get("decision", heuristic.decision),
                "summary": response.get("summary", heuristic.summary),
                "observations": response.get("observations", heuristic.observations),
                "suspected_causes": response.get("suspected_causes", heuristic.suspected_causes),
                "evidence_gaps": response.get("evidence_gaps", heuristic.evidence_gaps),
                "unresolved_questions": response.get("unresolved_questions", heuristic.unresolved_questions),
                "analysis_warnings": response.get("analysis_warnings", heuristic.analysis_warnings),
                "confidence": float(response.get("confidence", heuristic.confidence)),
            }
        )
    except Exception:  # pragma: no cover - best effort only
        return heuristic


async def _compare(payload: CompareAnalysesRequest) -> System3Result:
    primary_mapping = _primary_mapping_row(payload.system1.mentioned_columns, payload.system2.column_mapping)
    legacy_name = (
        primary_mapping.old_column_name
        if primary_mapping
        else (payload.old_analysis.relevant_columns[0] if payload.old_analysis.relevant_columns else "legacy field")
    )
    gavin3_name = (
        primary_mapping.new_column_name
        if primary_mapping and primary_mapping.new_column_name
        else (payload.new_analysis.relevant_columns[0] if payload.new_analysis.relevant_columns else "Gavin3 field")
    )
    mapping_phrase = _mapping_phrase(legacy_name, gavin3_name)
    issue_text = payload.system1.issue.lower()
    old_text = " ".join(payload.old_analysis.observations).lower()
    new_text = " ".join(payload.new_analysis.observations).lower()
    new_evidence_text = " ".join(item.snippet.lower() for item in payload.new_analysis.evidence)
    old_focus_seen = _column_seen_in_analysis(legacy_name, payload.old_analysis)
    new_focus_seen = _column_seen_in_analysis(gavin3_name, payload.new_analysis)
    source_gap_detected = _looks_like_source_handoff_gap(gavin3_name, payload.new_analysis)
    decision = "insufficient_evidence"
    root_cause_family = "insufficient_evidence"
    root_cause = f"There is not enough direct script evidence to confidently explain how {mapping_phrase} is handled in the new pipeline."

    if "derived with withcolumn" in old_text and not new_focus_seen:
        decision = "regression_detected"
        root_cause_family = "renamed_derivation"
        root_cause = f"Legacy derived field {mapping_phrase} is present in the old pipeline, but {gavin3_name} is not derived in the new pipeline."
    elif "join logic" in new_text and ("null" in issue_text or "null" in new_evidence_text):
        decision = "investigate_join_logic"
        root_cause_family = "join_null_spike"
        root_cause = f"Legacy field {mapping_phrase} may be impacted by new join logic, causing null enrichment or row completeness issues on {gavin3_name}."
    elif "filter logic" in new_text:
        decision = "investigate_filter_logic"
        root_cause_family = "filter_row_loss"
        root_cause = f"Legacy field {mapping_phrase} may be affected by a new Gavin3 filter that removes rows or suppresses {gavin3_name}."
    elif old_focus_seen and not new_focus_seen and source_gap_detected:
        decision = "upstream_source_check_required"
        root_cause_family = "source_column_disappearance"
        root_cause = f"Legacy field {mapping_phrase} is visible in the old pipeline, but the new pipeline only carries identifier or join-key handoff columns instead of {gavin3_name}, suggesting an upstream source gap."
    elif (
        not new_focus_seen
        and payload.new_analysis.evidence
        and "different target names" in new_text
        and _looks_like_alias_mismatch(gavin3_name, payload.new_analysis.evidence)
    ):
        decision = "regression_detected"
        root_cause_family = "alias_mismatch"
        root_cause = f"Mapped field {mapping_phrase} is exposed under a different Gavin3 alias in the new pipeline instead of {gavin3_name}."
    elif old_focus_seen and not new_focus_seen and payload.new_analysis.evidence:
        decision = "regression_detected"
        root_cause_family = "missing_final_select"
        root_cause = f"Legacy field {mapping_phrase} is carried in the old pipeline, but {gavin3_name} is not projected in the new pipeline."

    possible_resolutions = dedupe(
        [
            f"Verify the mapping {mapping_phrase} against the upstream source tables: {', '.join(payload.system2.source_tables)}.",
            f"Confirm that legacy field {legacy_name} should land in Gavin3 as {gavin3_name} according to the column mapping workbook.",
            f"Review the new transformation at {payload.system2.new_transformation_script_path} and ensure {gavin3_name} is selected, derived, or aliased exactly as expected.",
            f"If the Gavin3 business name differs by design, update downstream expectations and documentation for the mapping {mapping_phrase}.",
        ]
    )
    if decision == "insufficient_evidence":
        possible_resolutions = dedupe(
            possible_resolutions
            + [
                "Expand the retrieved script context to include upstream source selects and final output projection.",
                f"Validate whether the Jira title references the intended Gavin3 business name {gavin3_name}.",
            ]
        )

    final_summary = (
        f"{payload.system1.issue}: {root_cause} "
        f"Old analysis found {len(payload.old_analysis.evidence)} relevant code references, and new analysis found {len(payload.new_analysis.evidence)}."
    )
    heuristic_result = System3Result(
        system1=payload.system1,
        system2=payload.system2,
        old_analysis=payload.old_analysis,
        new_analysis=payload.new_analysis,
        prompt_version=PROMPT_VERSION,
        decision=decision,
        root_cause_family=root_cause_family,
        issue_impact=f"{payload.system1.issue} affects output table {payload.system2.new_target_table_name}.",
        old_script_observation=payload.old_analysis.summary,
        new_script_observation=payload.new_analysis.summary,
        likely_root_cause=root_cause,
        possible_resolutions=possible_resolutions,
        recommended_next_step=possible_resolutions[2],
        final_summary=final_summary,
        evidence_gaps=dedupe(payload.old_analysis.evidence_gaps + payload.new_analysis.evidence_gaps),
        unresolved_questions=dedupe(payload.old_analysis.unresolved_questions + payload.new_analysis.unresolved_questions),
        analysis_warnings=dedupe(payload.old_analysis.analysis_warnings + payload.new_analysis.analysis_warnings),
    )
    enriched = await _maybe_llm_synthesize(payload, heuristic_result)
    return enriched or heuristic_result


async def _maybe_llm_synthesize(
    payload: CompareAnalysesRequest,
    heuristic: System3Result,
) -> System3Result:
    if not LLM_CLIENT.enabled:
        return heuristic
    prompt = build_synthesis_prompt(payload)
    response = await LLM_CLIENT.complete_json(
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        debug_label="analysis_synthesis",
    )
    if not response:
        return heuristic
    try:
        return heuristic.model_copy(
            update={
                "prompt_version": response.get("prompt_version", PROMPT_VERSION),
                "decision": response.get("decision", heuristic.decision),
                "root_cause_family": response.get("root_cause_family", heuristic.root_cause_family),
                "issue_impact": response.get("issue_impact", heuristic.issue_impact),
                "old_script_observation": response.get("old_script_observation", heuristic.old_script_observation),
                "new_script_observation": response.get("new_script_observation", heuristic.new_script_observation),
                "likely_root_cause": response.get("likely_root_cause", heuristic.likely_root_cause),
                "possible_resolutions": response.get("possible_resolutions", heuristic.possible_resolutions),
                "recommended_next_step": response.get("recommended_next_step", heuristic.recommended_next_step),
                "final_summary": response.get("final_summary", heuristic.final_summary),
                "evidence_gaps": response.get("evidence_gaps", heuristic.evidence_gaps),
                "unresolved_questions": response.get("unresolved_questions", heuristic.unresolved_questions),
                "analysis_warnings": response.get("analysis_warnings", heuristic.analysis_warnings),
            }
        )
    except Exception:  # pragma: no cover - best effort only
        return heuristic


def _looks_like_alias_mismatch(focus_column: str, evidence: List[EvidenceRef]) -> bool:
    aliases = []
    for item in evidence:
        aliases.extend(re.findall(r'alias\(["\']([^"\']+)["\']\)', item.snippet, flags=re.IGNORECASE))
    if not aliases:
        return False
    normalized_focus = focus_column.lower()
    focus_prefix = normalized_focus.split("_")[0]
    return any(
        alias
        and alias.lower() != normalized_focus
        and alias.lower().startswith(focus_prefix)
        for alias in aliases
    )


def _looks_like_source_handoff_gap(focus_column: str, analysis: ScriptAnalysis) -> bool:
    if _column_seen_in_analysis(focus_column, analysis):
        return False
    lowered_obs = " ".join(analysis.observations).lower()
    return "only selects join keys or identifier fields" in lowered_obs


def _looks_like_identifier_only_select(script_text: str) -> bool:
    select_blocks = _extract_call_blocks(script_text, "select")
    for block in select_blocks:
        quoted_columns = re.findall(r'["\']([^"\']+)["\']', block)
        if quoted_columns and all(_looks_like_identifier_column(column) for column in quoted_columns):
            return True
    return False


def _looks_like_identifier_column(column_name: str) -> bool:
    lowered = normalize_key(column_name)
    identifier_tokens = ("_id", "identifier", "_key", "key_")
    return any(token in lowered for token in identifier_tokens)


def _extract_call_blocks(script_text: str, function_name: str) -> List[str]:
    blocks: List[str] = []
    lowered = script_text.lower()
    needle = f"{function_name.lower()}("
    start = 0
    while True:
        index = lowered.find(needle, start)
        if index == -1:
            return blocks
        cursor = index + len(needle)
        depth = 1
        while cursor < len(script_text) and depth > 0:
            char = script_text[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            cursor += 1
        if depth == 0:
            blocks.append(script_text[index + len(needle) : cursor - 1])
            start = cursor
        else:
            blocks.append(script_text[index + len(needle) :])
            return blocks


def _primary_mapping_row(mentioned_columns: List[str], mapping_rows: List):
    pairs = _derive_column_pairs(mentioned_columns, mapping_rows)
    if not pairs:
        return None
    target_old = pairs[0]["old_name"]
    target_new = pairs[0]["new_name"]
    for row in mapping_rows:
        if row.old_column_name == target_old and row.new_column_name == target_new:
            return row
    return mapping_rows[0]


def _mapping_phrase(legacy_name: str, gavin3_name: str) -> str:
    if legacy_name and gavin3_name and legacy_name != gavin3_name:
        return f"{legacy_name} -> {gavin3_name}"
    return gavin3_name or legacy_name or "the mapped field"




def _column_seen_in_analysis(focus_column: str, analysis: ScriptAnalysis) -> bool:
    target = normalize_key(focus_column)
    if not target:
        return False
    for item in analysis.evidence:
        identifiers = re.findall(r'["\']([^"\']+)["\']', item.snippet)
        if any(_identifier_matches_target(identifier, target) for identifier in identifiers):
            return True
    positive_observation_prefixes = (
        f"column {focus_column.lower()} appears in a select statement",
        f"column {focus_column.lower()} is created via alias",
        f"column {focus_column.lower()} is derived with withcolumn",
        f"column {focus_column.lower()} is explicitly dropped",
    )
    lowered_observations = [observation.lower() for observation in analysis.observations]
    return any(
        any(prefix in observation for prefix in positive_observation_prefixes)
        for observation in lowered_observations
    )


def _identifier_matches_target(identifier: str, target: str) -> bool:
    normalized = normalize_key(identifier)
    leaf = normalize_key(identifier.split(".")[-1])
    return target in {normalized, leaf}
