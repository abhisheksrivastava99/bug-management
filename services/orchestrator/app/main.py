import logging
import os
import sys
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.logging_utils import configure_logging
from bug_management_shared.models import (
    ChatInvestigateRequest,
    ChatInvestigateResponse,
    IncidentAnalysisRequest,
    ServiceStep,
    System1Result,
    System2Request,
    System3Result,
)


configure_logging("orchestrator")
LOGGER = logging.getLogger("orchestrator")
app = FastAPI(title="Bug Investigation Orchestrator", version="0.1.0")
SYSTEM1_URL = os.getenv("SYSTEM1_URL", "http://127.0.0.1:8001")
SYSTEM2_URL = os.getenv("SYSTEM2_URL", "http://127.0.0.1:8002")
SYSTEM3_URL = os.getenv("SYSTEM3_URL", "http://127.0.0.1:8003")
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "orchestrator"}


@app.get("/ready")
async def ready() -> dict:
    return {
        "status": "ready",
        "service": "orchestrator",
        "system1_url": SYSTEM1_URL,
        "system2_url": SYSTEM2_URL,
        "system3_url": SYSTEM3_URL,
    }


@app.get("/warmup")
async def warmup() -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        statuses = {
            "system1": await _probe_dependency(client, SYSTEM1_URL, "system1"),
            "system2": await _probe_dependency(client, SYSTEM2_URL, "system2"),
            "system3": await _probe_dependency(client, SYSTEM3_URL, "system3"),
        }
    return {
        "status": "warm" if all(item["ok"] for item in statuses.values()) else "partial",
        "service": "orchestrator",
        "dependencies": statuses,
    }


@app.post("/chat/investigate", response_model=ChatInvestigateResponse)
async def investigate(
    payload: ChatInvestigateRequest,
    x_request_id: str = Header(default=None),
) -> ChatInvestigateResponse:
    request_id = x_request_id or str(uuid.uuid4())
    headers = {"X-Request-ID": request_id}
    steps = [
        ServiceStep(name="system1", status="running", detail="Parsing Jira title."),
        ServiceStep(name="system2", status="pending", detail="Waiting for metadata lookup."),
        ServiceStep(name="system3", status="pending", detail="Waiting for script analysis."),
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        system1_res = await client.post(
            f"{SYSTEM1_URL}/parse-and-classify",
            json={"raw_title": payload.raw_title},
            headers=headers,
        )
        _raise_for_status(system1_res, "system1")
        system1 = System1Result(**system1_res.json())
        steps[0] = ServiceStep(name="system1", status="completed", detail=system1.issue_classification)

        if system1.issue_classification == "infra_issue":
            steps[1] = ServiceStep(name="system2", status="skipped", detail="Infra issues do not require metadata lookup.")
            steps[2] = ServiceStep(name="system3", status="skipped", detail="Infra issues do not require script analysis.")
            markdown = _format_infra_markdown(system1)
            return ChatInvestigateResponse(
                request_id=request_id,
                routing_team=system1.routing_team,
                system1=system1,
                final_summary=f"Infra issue routed to {system1.routing_team}: {system1.issue}",
                markdown_summary=markdown,
                steps=steps,
            )

        steps[1] = ServiceStep(name="system2", status="running", detail="Resolving metadata and mappings.")
        system2_res = await client.post(
            f"{SYSTEM2_URL}/resolve-metadata",
            json=System2Request(
                division=system1.division,
                table_name=system1.table_name,
                issue=system1.issue,
                mentioned_columns=system1.mentioned_columns,
            ).dict(),
            headers=headers,
        )
        _raise_for_status(system2_res, "system2")
        system2_payload = system2_res.json()
        steps[1] = ServiceStep(name="system2", status="completed", detail=system2_payload["support_team"])

        steps[2] = ServiceStep(name="system3", status="running", detail="Analyzing old and new scripts.")
        system3_res = await client.post(
            f"{SYSTEM3_URL}/analyze-incident",
            json=IncidentAnalysisRequest(
                system1=system1,
                system2=system2_payload,
            ).dict(),
            headers=headers,
        )
        _raise_for_status(system3_res, "system3")
        system3 = System3Result(**system3_res.json())
        steps[2] = ServiceStep(name="system3", status="completed", detail="Investigation complete.")
        markdown = _format_markdown(system3)
        return ChatInvestigateResponse(
            request_id=request_id,
            routing_team=system1.routing_team,
            system1=system1,
            system2=system2_payload,
            system3=system3,
            final_summary=system3.final_summary,
            markdown_summary=markdown,
            steps=steps,
        )


def _raise_for_status(response: httpx.Response, service_name: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        LOGGER.error("%s call failed: %s", service_name, exc)
        raise HTTPException(status_code=502, detail=f"{service_name} request failed: {response.text}")


async def _probe_dependency(client: httpx.AsyncClient, base_url: str, service_name: str) -> dict:
    try:
        response = await client.get(f"{base_url}/ready")
        response.raise_for_status()
        return {"ok": True, "detail": response.json()}
    except Exception as exc:  # pragma: no cover - best effort only
        LOGGER.warning("%s warmup probe failed: %s", service_name, exc)
        return {"ok": False, "detail": str(exc)}


def _format_infra_markdown(system1: System1Result) -> str:
    return (
        f"## Investigation Summary\n"
        f"- Classification: {system1.issue_classification}\n"
        f"- Routing Team: {system1.routing_team}\n"
        f"- Issue: {system1.issue}\n"
        f"- Recommendation: Hand off to infra responders and verify runtime health before data triage."
    )


def _format_markdown(system3: System3Result) -> str:
    resolutions = "\n".join(f"- {item}" for item in system3.possible_resolutions)
    return (
        f"## Investigation Summary\n"
        f"- Routing Team: {system3.system1.routing_team}\n"
        f"- Division/Table: {system3.system1.division}/{system3.system1.table_name}\n"
        f"- Issue: {system3.system1.issue}\n\n"
        f"## Findings\n"
        f"- Impact: {system3.issue_impact}\n"
        f"- Old Script: {system3.old_script_observation}\n"
        f"- New Script: {system3.new_script_observation}\n"
        f"- Likely Root Cause: {system3.likely_root_cause}\n\n"
        f"## Possible Resolutions\n"
        f"{resolutions}\n\n"
        f"## Recommended Next Step\n"
        f"{system3.recommended_next_step}"
    )
