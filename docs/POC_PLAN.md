# POC Plan: Multi-Service Jira Bug Investigation Chatbot With Smoke Testing

## Summary
- Build a monorepo with four FastAPI apps and one React/Vite app: System 1, System 2, System 3, and a chat orchestrator. Keep the three systems independently runnable and deployable; the orchestrator is the only backend the chat UI calls.
- Use repo-local mock Excel files and dummy old/new PySpark scripts. The user manually pastes a Jira title into the chatbot; no direct Jira integration in v1.
- Implement hybrid RAG without a vector DB: System 2 deterministically retrieves metadata/mappings from Excel, and System 3 retrieves only the relevant script sections from local files before sending grounded prompts to the LLM.
- Add smoke testing for each service and for the full chain so the stack can be validated quickly after startup or deployment.

## Key APIs And Types
- Shared Pydantic models in `packages/shared`: `System1Request`, `System1Result`, `System2Request`, `ResolvedMetadata`, `ScriptAnalysisRequest`, `ScriptAnalysis`, `System3Result`, `ChatInvestigateRequest`, `ChatInvestigateResponse`, and `EvidenceRef`.
- System 1 FastAPI:
  - `POST /parse-and-classify` parses `raw_title`, normalizes `division` and `table_name`, extracts `issue`, `mentioned_columns`, `issue_classification`, `routing_team`, and `confidence`.
- System 2 FastAPI:
  - `POST /resolve-metadata` performs deterministic Excel lookup by `division` and `table_name`, then returns table metadata plus focused `column_mapping` rows filtered by `mentioned_columns` when present.
- System 3 FastAPI:
  - `POST /analyze-old-script`
  - `POST /analyze-new-script`
  - `POST /compare-analyses`
  - `POST /analyze-incident` as a convenience endpoint that runs old/new analysis in parallel, then synthesis; this is the endpoint the orchestrator calls.
- Orchestrator FastAPI:
  - `POST /chat/investigate` calls System 1, short-circuits infra issues, otherwise calls System 2, then System 3, and returns final JSON plus a chat-friendly formatted summary.
- Common operational endpoints on every backend:
  - `GET /health` for liveness
  - `GET /ready` for dependency/config readiness
- React/Vite UI:
  - Single chat page with Jira title input, submit button, step status for Systems 1-3, final summary card, and expandable raw JSON.

## Implementation Changes
- Repo layout: `services/*` for the four backends, `apps/chat-ui` for the frontend, and `packages/shared` for schemas, prompt builders, common utilities, and test fixtures.
- System 1 is rules-first: regex for `DIVISION_TABLENAME_ISSUE`, keyword routing for infra vs data issues, and LLM fallback only when parsing or classification confidence is low. Title parsing is case-insensitive and tolerant of extra spaces or underscore variation.
- System 2 loads the two Excel files at startup, caches them in memory, normalizes lookup keys, returns owners/support/script paths, and extracts column-focused mapping rows using deterministic logic only. No LLM calls are allowed in System 2.
- System 3 uses local file retrieval instead of embeddings: load the old/new scripts from resolved paths, extract relevant code chunks by target table, mentioned columns, and PySpark operations such as `select`, `withColumn`, `alias`, `join`, `filter`, `drop`, and rename patterns.
- Old and new analysis prompts are isolated: each endpoint sees only one script, the incident context, and resolved metadata. Each returns structured JSON with observations, suspected behavior, and `evidence` line references.
- The compare step synthesizes the two analyses into `issue_impact`, `old_script_observation`, `new_script_observation`, `likely_root_cause`, `possible_resolutions`, `recommended_next_step`, and `final_summary`. It must only use System 1 output, System 2 output, and the two script analyses.
- Add basic observability: propagated request IDs from the orchestrator, structured logs per step, and startup validation for required files and LLM configuration.
- Run the full demo with Docker Compose so every FastAPI app and the React app stay independent but can start together.
- Add a smoke-test runner that hits live endpoints after startup:
  - service smoke tests for Systems 1-3 and orchestrator
  - one end-to-end smoke test that submits a known Jira title and validates the expected response shape and key fields
  - one infra-routing smoke test that confirms the flow stops after System 1

## Test Plan
- Unit and contract tests:
  - System 1: valid title parsing, mixed-case and spacing tolerance, infra routing, malformed-title fallback, and `mentioned_columns` extraction from issues like `Column date_updated missing`.
  - System 2: deterministic metadata lookup, exact/renamed/dropped mapping cases, missing-table handling, missing-column handling, and stable JSON output from repo-local Excel fixtures.
  - System 3: old script detects retained column logic, new script detects dropped or renamed logic, compare step explains the regression using returned evidence, unreadable script paths fail gracefully with actionable errors, and prompts do not include unrelated script sections.
- Smoke tests against running services:
  - `GET /health` and `GET /ready` for all four backends.
  - `POST /parse-and-classify` with a known data issue title and a known infra issue title.
  - `POST /resolve-metadata` with a known table and known column reference.
  - `POST /analyze-incident` with fixture System 1 and System 2 payloads.
  - `POST /chat/investigate` with one missing-column bug and one infra bug.
- End-to-end scenarios:
  - missing-column regression
  - renamed-column regression
  - infra issue that short-circuits before Systems 2 and 3
- Smoke-test acceptance criteria:
  - all services start cleanly in Docker Compose
  - readiness checks pass
  - live endpoint responses match required JSON shape
  - end-to-end chat response contains `likely_root_cause`, `possible_resolutions`, and `recommended_next_step`

## Assumptions
- POC only: no auth, no persistent chat history, no direct Jira API integration, and no background queueing.
- Repo-local mock Excel files and dummy PySpark scripts are the source of truth for the demo.
- Only `data_table_issue` incidents proceed to Systems 2 and 3; `infra_issue` responses return immediately with routing guidance.
- "RAG" in this POC means grounded retrieval of Excel rows and relevant script chunks, not a vector database. If recall becomes a problem later, the first upgrade path is script-chunk embeddings inside System 3 without changing System 2.
- Smoke tests run against live local services and are intended as fast deployment/startup validation, not a replacement for deeper automated tests.
