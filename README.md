# Bug Management POC

Multi-service Jira bug investigation chatbot POC with:

- `system1`: Jira title parsing and issue classification
- `system2`: metadata and column mapping resolution
- `system3`: old/new script analysis and incident synthesis
- `orchestrator`: chat-facing API that runs the full flow
- `apps/chat-ui`: minimal React/Vite frontend
  - now includes both the bug investigation view and an Azure observability dashboard at `/#/observability`

## Quick Start

1. Create a Python environment and install `requirements.txt`.
2. Add your API key to `.env` at the repo root:
   - `OPENAI_API_KEY="..."`
3. Generate fixture Excel files:
   - `python3 scripts/generate_excel_fixtures.py`
   - observability-only mock LAW fixtures can also be regenerated with `python3 scripts/generate_observability_fixtures.py`
4. Start services:
   - `uvicorn app.main:app --reload --port 8001` from `services/system1`
   - `uvicorn app.main:app --reload --port 8002` from `services/system2`
   - `uvicorn app.main:app --reload --port 8003` from `services/system3`
   - `uvicorn app.main:app --reload --port 8000` from `services/orchestrator`
5. Start the frontend:
   - `npm install`
   - `npm run dev`

## Render Deployment

This repo includes a demo-friendly Render setup in [`render.yaml`](/Users/abhishek/Desktop/Projects/Bug%20Management/render.yaml):

- `bug-management-api`
  - one unified FastAPI backend for deployment
  - reuses the current System 1, System 2, and System 3 logic in a single service
- `bug-management-ui`
  - static React/Vite frontend
  - reads `VITE_API_BASE_URL` from the backend service URL

Render setup notes:

1. Connect the repo in Render and create services from `render.yaml`.
2. Set `OPENAI_API_KEY` when Render prompts for secret environment variables.
3. Deploy the backend and frontend.
4. Open the frontend URL and use the `Wake Backend` button before demoing if the backend is on the free tier.

The deployed backend entrypoint is:

- `services/render_backend/app/main.py`

It exposes:

- `GET /health`
- `GET /ready`
- `GET /warmup`
- `POST /chat/investigate`

## Tests

- Unit tests: `python3 -m unittest discover -s tests/unit -p "test_*.py"`
- Smoke tests against live services:
  `python3 tests/smoke/run_smoke_tests.py`
- Prompt evaluation:
  - Mocked mode: `python3 tests/prompt_eval/run_prompt_eval.py --mode mocked`
  - Live mode: `OPENAI_API_KEY=... python3 tests/prompt_eval/run_prompt_eval.py --mode live`

## Fixture Generation

- Regenerate the dynamic fixture catalog, Excel files, and paired old/new scripts:
  `python3 scripts/generate_excel_fixtures.py`
- Optional deterministic variation:
  `BM_FIXTURE_SEED=17 python3 scripts/generate_excel_fixtures.py`
