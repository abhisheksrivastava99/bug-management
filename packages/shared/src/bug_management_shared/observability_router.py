from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .observability_models import (
    ObservabilityCadence,
    ObservabilityFilters,
    ObservabilityPipelineDetailResponse,
    ObservabilityPipelinesResponse,
    ObservabilityQueryRequest,
    ObservabilityQueryResponse,
    ObservabilityStatus,
    ObservabilitySummaryAIRequest,
    ObservabilitySummaryAIResponse,
    ObservabilitySummaryResponse,
)
from .observability_service import ObservabilityService


router = APIRouter(prefix="/observability", tags=["observability"])
OBSERVABILITY_SERVICE = ObservabilityService()


@router.get("/summary", response_model=ObservabilitySummaryResponse)
async def observability_summary(
    window_days: int = Query(default=30, ge=7, le=365),
    cadence: Optional[ObservabilityCadence] = None,
    status: Optional[ObservabilityStatus] = None,
    owner: Optional[str] = None,
    criticality: Optional[str] = None,
    search: Optional[str] = None,
) -> ObservabilitySummaryResponse:
    filters = _build_filters(window_days, cadence, status, owner, criticality, search)
    return OBSERVABILITY_SERVICE.get_summary(filters)


@router.get("/pipelines", response_model=ObservabilityPipelinesResponse)
async def observability_pipelines(
    window_days: int = Query(default=30, ge=7, le=365),
    cadence: Optional[ObservabilityCadence] = None,
    status: Optional[ObservabilityStatus] = None,
    owner: Optional[str] = None,
    criticality: Optional[str] = None,
    search: Optional[str] = None,
) -> ObservabilityPipelinesResponse:
    filters = _build_filters(window_days, cadence, status, owner, criticality, search)
    return OBSERVABILITY_SERVICE.get_pipelines(filters)


@router.get("/pipelines/{pipeline_name}", response_model=ObservabilityPipelineDetailResponse)
async def observability_pipeline_detail(
    pipeline_name: str,
    window_days: int = Query(default=30, ge=7, le=365),
    cadence: Optional[ObservabilityCadence] = None,
    status: Optional[ObservabilityStatus] = None,
    owner: Optional[str] = None,
    criticality: Optional[str] = None,
    search: Optional[str] = None,
) -> ObservabilityPipelineDetailResponse:
    filters = _build_filters(window_days, cadence, status, owner, criticality, search)
    try:
        return OBSERVABILITY_SERVICE.get_pipeline_detail(pipeline_name, filters)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/summary-ai", response_model=ObservabilitySummaryAIResponse)
async def observability_summary_ai(payload: ObservabilitySummaryAIRequest) -> ObservabilitySummaryAIResponse:
    return await OBSERVABILITY_SERVICE.get_summary_ai(payload)


@router.post("/query", response_model=ObservabilityQueryResponse)
async def observability_query(payload: ObservabilityQueryRequest) -> ObservabilityQueryResponse:
    return await OBSERVABILITY_SERVICE.run_query(payload)


def _build_filters(
    window_days: int,
    cadence: Optional[ObservabilityCadence],
    status: Optional[ObservabilityStatus],
    owner: Optional[str],
    criticality: Optional[str],
    search: Optional[str],
) -> ObservabilityFilters:
    return ObservabilityFilters(
        window_days=window_days,
        cadence=cadence,
        status=status,
        owner=owner,
        criticality=criticality,
        search=search,
    )
