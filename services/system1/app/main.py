import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.llm import OpenAIChatClient
from bug_management_shared.logging_utils import configure_logging
from bug_management_shared.models import System1Request, System1Result
from bug_management_shared.text_utils import extract_candidate_columns, normalize_issue_text


configure_logging("system1")
LOGGER = logging.getLogger("system1")
app = FastAPI(title="System 1 - Jira Title Parser & Classifier", version="0.1.0")
LLM_CLIENT = OpenAIChatClient()
TITLE_RE = re.compile(r"^\s*([A-Za-z0-9]+)[_\s]+([A-Za-z0-9]+)[_\s]+(.+?)\s*$")
INFRA_KEYWORDS = {
    "cluster",
    "scheduler",
    "network",
    "filesystem",
    "resource",
    "timeout",
    "disk",
    "permission",
    "oom",
    "infra",
    "spark failure",
    "job failed",
}
DATA_KEYWORDS = {
    "column",
    "missing",
    "null",
    "mapping",
    "wrong value",
    "table",
    "join",
    "duplicate",
    "rename",
    "renamed",
    "data",
}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "system1"}


@app.get("/ready")
async def ready() -> dict:
    return {
        "status": "ready",
        "service": "system1",
        "llm_enabled": LLM_CLIENT.enabled,
    }


@app.post("/parse-and-classify", response_model=System1Result)
async def parse_and_classify(payload: System1Request) -> System1Result:
    parsed = _parse_title(payload.raw_title)
    result = _classify(parsed)
    if result.confidence < 0.7:
        enriched = await _maybe_llm_classify(payload.raw_title)
        if enriched:
            result = enriched
    if not result.issue:
        raise HTTPException(status_code=422, detail="unable to parse issue text")
    return result


def _parse_title(raw_title: str) -> System1Result:
    match = TITLE_RE.match(raw_title)
    notes = []
    if not match:
        sanitized = re.sub(r"[_\s]+", " ", raw_title.strip())
        tokens = sanitized.split(" ", 2)
        if len(tokens) < 3:
            raise HTTPException(
                status_code=422,
                detail="title must look like DIVISION_TABLENAME_ISSUE",
            )
        division, table_name, issue = tokens[0], tokens[1], tokens[2]
        notes.append("Fallback parser used due to title format variation.")
    else:
        division, table_name, issue = match.groups()

    issue = normalize_issue_text(issue)
    return System1Result(
        raw_title=raw_title,
        division=division.upper(),
        table_name=table_name.upper(),
        issue=issue,
        mentioned_columns=extract_candidate_columns(issue),
        issue_classification="unknown_issue",
        routing_team="triage_team",
        confidence=0.45,
        parsing_notes=notes,
    )


def _classify(parsed: System1Result) -> System1Result:
    lowered = parsed.issue.lower()
    infra_hits = sum(1 for item in INFRA_KEYWORDS if item in lowered)
    data_hits = sum(1 for item in DATA_KEYWORDS if item in lowered)

    classification = "unknown_issue"
    routing_team = "triage_team"
    confidence = 0.55

    if infra_hits > data_hits and infra_hits > 0:
        classification = "infra_issue"
        routing_team = "infra_team"
        confidence = 0.93
    elif data_hits >= infra_hits and data_hits > 0:
        classification = "data_table_issue"
        routing_team = "data_team"
        confidence = 0.95 if "column" in lowered or "missing" in lowered else 0.88

    return parsed.model_copy(
        update={
            "issue_classification": classification,
            "routing_team": routing_team,
            "confidence": confidence,
        }
    )


async def _maybe_llm_classify(raw_title: str) -> Optional[System1Result]:
    prompt = f"""
Return JSON with keys division, table_name, issue, mentioned_columns, issue_classification, routing_team, confidence.
Title: {raw_title}
Classify as infra_issue, data_table_issue, or unknown_issue.
""".strip()
    response = await LLM_CLIENT.complete_json(
        system_prompt="You extract structured incident data from Jira bug titles.",
        user_prompt=prompt,
    )
    if not response:
        return None
    try:
        return System1Result(
            raw_title=raw_title,
            division=str(response["division"]).upper(),
            table_name=str(response["table_name"]).upper(),
            issue=normalize_issue_text(str(response["issue"])),
            mentioned_columns=response.get("mentioned_columns", []),
            issue_classification=response.get("issue_classification", "unknown_issue"),
            routing_team=response.get("routing_team", "triage_team"),
            confidence=float(response.get("confidence", 0.6)),
            parsing_notes=["LLM fallback used due to low rule confidence."],
        )
    except Exception as exc:  # pragma: no cover - best effort only
        LOGGER.warning("llm fallback parse failed: %s", exc)
        return None
