import json
from typing import Dict, List

from .observability_models import (
    ObservabilityCadenceGroup,
    ObservabilityQueryResult,
    ObservabilitySummaryResponse,
)


PROMPT_VERSION = "observability.v1"


def build_summary_prompt(summary: ObservabilitySummaryResponse, groups: List[ObservabilityCadenceGroup]) -> Dict[str, str]:
    system_prompt = (
        f"You are the dashboard_summary prompt in {PROMPT_VERSION}. "
        "Summarize the provided dashboard metrics only. Do not invent new data, do not generate queries, "
        "and keep the response concise and operationally useful."
    )
    user_prompt = f"""
## Dashboard Summary
{_json_dump(summary)}

## Cadence Groups
{json.dumps([_model_to_dict(group) for group in groups], indent=2)}

## Output JSON Schema
Return a JSON object with exactly these keys:
- title: string
- summary: string
- insights: array of 2 to 4 strings
- caveat: string or null
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def build_query_translation_prompt(question: str, filters: dict) -> Dict[str, str]:
    system_prompt = (
        f"You are the query_translation prompt in {PROMPT_VERSION}. "
        "Convert a natural-language question into a safe observability query plan and a display-only KQL query. "
        "You must choose exactly one supported intent and stay within the allowed datasets and metrics."
    )
    user_prompt = f"""
## User Question
{question}

## Active Filters
{json.dumps(filters, indent=2)}

## Allowed Intents
- success_rate_by_pipeline
- run_count_by_cadence
- average_duration_trend
- recent_failures
- slowest_pipelines
- pipelines_with_retries
- last_run_status
- unsupported

## Allowed Datasets
- pipeline_runs

## Allowed Metrics
- success_rate
- run_count
- average_duration
- retry_count
- last_run_status

## Output JSON Schema
Return a JSON object with exactly these keys:
- intent: string
- dataset: string
- metric: string
- time_window_days: number
- cadence: string or null
- pipeline_name: string or null
- group_by: array of strings
- filters: object
- sort_field: string or null
- sort_direction: string
- limit: number
- visualization: string or null
- display_kql: string
- confidence: number between 0 and 1
- warnings: array of strings
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def build_query_summary_prompt(question: str, result: ObservabilityQueryResult, warnings: List[str]) -> Dict[str, str]:
    system_prompt = (
        f"You are the query_results_summary prompt in {PROMPT_VERSION}. "
        "Summarize executed observability query results. Ground every statement in the provided rows."
    )
    user_prompt = f"""
## User Question
{question}

## Executed Result
{_json_dump(result)}

## Validation Warnings
{json.dumps(warnings, indent=2)}

## Output JSON Schema
Return a JSON object with exactly these keys:
- summary: string
- insights: array of 2 to 4 strings
- caveats: array of strings
- follow_ups: array of 2 to 3 strings
""".strip()
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def _json_dump(model) -> str:
    return json.dumps(_model_to_dict(model), indent=2)


def _model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
