import logging
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / "packages" / "shared" / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.logging_utils import configure_logging
from bug_management_shared.models import (
    ChatInvestigateRequest,
    ChatInvestigateResponse,
    IncidentAnalysisRequest,
    ServiceStep,
    System1Request,
    System2Request,
    System4Request,
)
from bug_management_shared.system4 import analyze_system4
from services.system1.app.main import parse_and_classify
from services.system2.app.main import ready as system2_ready
from services.system2.app.main import resolve_metadata
from services.system2.app.main import startup as system2_startup
from services.system3.app.main import analyze_incident
from services.system3.app.main import ready as system3_ready


configure_logging("render-backend")
LOGGER = logging.getLogger("render-backend")
app = FastAPI(title="Bug Investigation Render Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    system2_startup()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "render-backend"}


@app.get("/ready")
async def ready() -> dict:
    system2_state = await system2_ready()
    system3_state = await system3_ready()
    return {
        "status": "ready",
        "service": "render-backend",
        "system2": system2_state,
        "system3": system3_state,
    }


@app.get("/warmup")
async def warmup() -> dict:
    payload = await ready()
    payload["warmed"] = True
    return payload


@app.post("/chat/investigate", response_model=ChatInvestigateResponse)
async def investigate(
    payload: ChatInvestigateRequest,
    x_request_id: str = Header(default=None),
) -> ChatInvestigateResponse:
    request_id = x_request_id or str(uuid.uuid4())
    steps = [
        ServiceStep(name="system1", status="running", detail="Parsing Jira title."),
        ServiceStep(name="system2", status="pending", detail="Waiting for metadata lookup."),
        ServiceStep(name="system3", status="pending", detail="Waiting for script analysis."),
        ServiceStep(name="system4", status="pending", detail="Waiting for SQL diagnostics."),
    ]

    system1 = await parse_and_classify(System1Request(raw_title=payload.raw_title))
    steps[0] = ServiceStep(name="system1", status="completed", detail=system1.issue_classification)

    if system1.issue_classification == "infra_issue":
        steps[1] = ServiceStep(name="system2", status="skipped", detail="Infra issues do not require metadata lookup.")
        steps[2] = ServiceStep(name="system3", status="skipped", detail="Infra issues do not require script analysis.")
        steps[3] = ServiceStep(name="system4", status="skipped", detail="Infra issues do not require SQL diagnostics.")
        markdown = _format_infra_markdown(system1.issue_classification, system1.routing_team, system1.issue)
        return ChatInvestigateResponse(
            request_id=request_id,
            routing_team=system1.routing_team,
            system1=system1,
            final_summary=f"Infra issue routed to {system1.routing_team}: {system1.issue}",
            markdown_summary=markdown,
            steps=steps,
        )

    steps[1] = ServiceStep(name="system2", status="running", detail="Resolving metadata and mappings.")
    system2 = await resolve_metadata(
        System2Request(
            division=system1.division,
            table_name=system1.table_name,
            issue=system1.issue,
            mentioned_columns=system1.mentioned_columns,
        )
    )
    steps[1] = ServiceStep(name="system2", status="completed", detail=system2.support_team)

    steps[2] = ServiceStep(name="system3", status="running", detail="Analyzing old and new scripts.")
    system3 = await analyze_incident(
        IncidentAnalysisRequest(
            system1=system1,
            system2=system2,
        )
    )
    steps[2] = ServiceStep(name="system3", status="completed", detail="New script comparison complete.")
    steps[3] = ServiceStep(name="system4", status="running", detail="Comparing SQLite data with the new script analysis.")
    system4 = await analyze_system4(
        System4Request(
            system1=system1,
            system2=system2,
            new_analysis=system3.new_analysis,
        )
    )
    steps[3] = ServiceStep(name="system4", status="completed", detail="SQL comparison complete.")

    return ChatInvestigateResponse(
        request_id=request_id,
        routing_team=system1.routing_team,
        system1=system1,
        system2=system2,
        system3=system3,
        system4=system4,
        final_summary=system4.summary or system3.final_summary,
        markdown_summary=_format_markdown(system3, system4),
        steps=steps,
    )


def _format_infra_markdown(issue_classification: str, routing_team: str, issue: str) -> str:
    return (
        "## Investigation Summary\n"
        f"- Classification: {issue_classification}\n"
        f"- Routing Team: {routing_team}\n"
        f"- Issue: {issue}\n"
        "- Recommendation: Hand off to infra responders and verify runtime health before data triage."
    )


def _format_markdown(system3, system4) -> str:
    resolutions = "\n".join(f"- {item}" for item in system3.possible_resolutions)
    sql_findings = "\n".join(f"- {item}" for item in system4.issue_findings) or "- No SQL findings were returned."
    sql_explanations = "\n".join(f"- {item}" for item in system4.explanation_points) or "- No SQL explanation points were returned."
    return (
        "## Investigation Summary\n"
        f"- Routing Team: {system3.system1.routing_team}\n"
        f"- Division/Table: {system3.system1.division}/{system3.system1.table_name}\n"
        f"- Issue: {system3.system1.issue}\n\n"
        "## Findings\n"
        f"- Impact: {system3.issue_impact}\n"
        f"- Old Script: {system3.old_script_observation}\n"
        f"- New Script: {system3.new_script_observation}\n"
        f"- Likely Root Cause: {system3.likely_root_cause}\n\n"
        "## SQL vs New Script\n"
        f"- Target Table: {system4.target_table}\n"
        f"- SQL Summary: {system4.summary}\n"
        f"- SQL Findings:\n{sql_findings}\n"
        f"- Comparison Points:\n{sql_explanations}\n\n"
        "## Possible Resolutions\n"
        f"{resolutions}\n\n"
        "## Recommended Next Step\n"
        f"{system3.recommended_next_step}"
    )
