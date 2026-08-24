# Fishora

Fishora is an AI catch-intelligence platform for Indonesian capture fisheries. A DINOv3 image
classifier identifies a landed fish, a human confirms or corrects it, and retrieval-augmented
generation turns the verified species into a grounded, source-cited commercial knowledge card in
Bahasa Indonesia.

The local runtime starts PostgreSQL in Docker and runs the CV service, the API, and the web frontend
from one command. Only the database is containerised: the CV service needs direct GPU access, so the
Python services run on the host.

## System at a Glance

| Service | Port | Runs on | Responsibility |
| --- | --- | --- | --- |
| Frontend (Next.js 16) | 3000 | Host, Node | Operator flow, marketplace, public QR profile |
| Main API (FastAPI) | 8000 | Host, Python | Identification, verification, knowledge cards |
| CV service (FastAPI) | 8001 | Host, Python + CUDA | DINOv3 species classification |
| PostgreSQL + pgvector | 55432 | Docker | Species, knowledge chunks and embeddings, predictions |

The browser talks to the Main API directly, so two settings must agree or every request fails:
`NEXT_PUBLIC_API_BASE_URL` (where the frontend sends requests) and `FISHORA_CORS_ALLOW_ORIGINS`
(which browser origins the API accepts). `scripts/run_local.sh` derives both from the port variables,
so changing a port keeps them in step automatically.

```text
Browser ──HTTP──> Frontend :3000
   │
   └────HTTP────> Main API :8000 ──> CV service :8001 ──> DINOv3 (CUDA)
                      │
                      ├──> PostgreSQL + pgvector :55432
                      └──> OpenCode Go (knowledge card generation)
```

## API Surface

These three endpoints exist today and are what the frontend integrates against:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/fish/identify` | Multipart image upload, returns a prediction and ranked candidates |
| POST | `/api/v1/fish/verify` | Human confirms or corrects the predicted species |
| GET | `/api/v1/predictions/{id}/knowledge` | Grounded knowledge card for a **verified** prediction |

Interactive docs: `http://localhost:8000/docs`.

A knowledge card is only issued for a verified prediction. Requesting one for a pending prediction
returns `409` by design: an AI guess must not become a public commercial record.

The commerce surfaces in the PRD (lots, bidding, buyer preferences, matching, QR, public consumer
profile, auth) are **not built yet**. See
`docs/plans/2026-08-24-fishora-frontend-and-ai-integration.md` for the implementation plan.

## Prerequisites

- Python 3.11
- Node.js 20.9 or newer (22.x recommended) and pnpm 10
- Docker with Docker Compose
- An NVIDIA GPU with a CUDA-compatible driver
- A model export containing `model_state_dict.pt`, `inference_config.json`, and `inference.py`

The default model export path is `ai/results/fishora_dinov3_large_frozen/export`.

## Setup

### 1. Python environment

Create one virtual environment and install CUDA-enabled PyTorch before installing Fishora:

```bash
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install -e '.[cv,dev]'
```

On Windows, the interpreter lives in `.venv/Scripts/` rather than `.venv/bin/`. Substitute
`.venv/Scripts/python.exe -m pip` for `.venv/bin/pip` throughout. `run_local.sh` detects either
layout on its own, so the run command below is the same either way.

Verify that PyTorch can access the GPU:

```bash
.venv/bin/python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

Cache the embedding model once while internet access is available. Runtime loading is offline-only.

```bash
.venv/bin/python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("intfloat/multilingual-e5-base")'
```

### 2. Frontend dependencies

```bash
cd apps/frontend
pnpm install
cd ../..
```

### 3. Configuration

Defaults are ready for local use. Create `.env` only to override them or to supply an OpenCode Go
API key for generated knowledge cards:

```bash
cp .env.example .env
```

Without `OPENCODE_GO_API_KEY` everything still starts, and identification and verification work
normally; only knowledge card generation fails, with a `502`.

Never commit `.env` or API keys.

## Run

Start the whole stack:

```bash
bash scripts/run_local.sh
```

The script verifies CUDA, starts PostgreSQL, applies migrations, seeds taxonomy data, then launches
the CV service, the API, and the frontend. It prints the resolved URLs, the API base the frontend
will call, and the CORS allow-list, so a mismatch is visible before you open a browser. DINOv3 runs
on CUDA while multilingual E5 embeddings run on CPU.

Stop with `Ctrl+C`. All three processes are terminated; PostgreSQL stays up in Docker:

```bash
docker compose down
```

### Running a subset

```bash
# Backend and CV only, no Node required
FISHORA_SKIP_FRONTEND=1 bash scripts/run_local.sh

# Frontend alone, against an API already running elsewhere
cd apps/frontend && pnpm dev
```

Run standalone, the frontend defaults to `http://localhost:8000` for the API. Point it elsewhere with
`NEXT_PUBLIC_API_BASE_URL`, and remember to add that frontend's origin to
`FISHORA_CORS_ALLOW_ORIGINS` on the API side.

### Avoiding port conflicts

Override any port; the derived URLs and CORS list follow:

```bash
FISHORA_FRONTEND_PORT=3111 FISHORA_MAIN_API_PORT=8080 bash scripts/run_local.sh
```

### Testing on a real phone

The dev server binds `0.0.0.0`, so a phone on the same network can open
`http://<your-machine-ip>:3000`. DESIGN.md treats mobile as the primary target, and layout at 390px
cannot be judged from a desktop browser. For the phone to reach the API, use your machine's address
on both sides:

```bash
FISHORA_CORS_ALLOW_ORIGINS="http://192.168.1.20:3000" \
NEXT_PUBLIC_API_BASE_URL="http://192.168.1.20:8000" \
bash scripts/run_local.sh
```

## Verify the Services

```bash
curl -fsS http://localhost:8001/health                       # CV service: status and model_version
curl -fsS http://localhost:8000/openapi.json | head -c 200   # API is serving
```

Confirm the browser is actually allowed to call the API. An empty `access-control-allow-origin` here
is the cause of nearly every "the frontend cannot reach the backend" report:

```bash
curl -si -X OPTIONS http://localhost:8000/api/v1/fish/identify \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' | grep -i access-control-allow-origin
```

Then open `http://localhost:3000`.

## Run Tests

### Backend

Tests that need neither PostgreSQL nor real model artifacts:

```bash
.venv/bin/python -m pytest -m "not integration and not real_artifact" -q
```

Integration tests, which need the database and migrations:

```bash
docker compose up -d db
export FISHORA_DATABASE_URL=postgresql+psycopg://fishora:fishora@localhost:55432/fishora
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest -m integration -q
```

### Frontend

```bash
cd apps/frontend
pnpm test     # Vitest unit and component tests
pnpm lint
pnpm build    # type check plus production build
```

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Browser console shows a CORS error | The frontend's origin is not in `FISHORA_CORS_ALLOW_ORIGINS`. Run the OPTIONS check above. Changing `FISHORA_FRONTEND_PORT` without restarting the API is the usual cause |
| `pnpm not found`, backend starts anyway | Install pnpm, or keep going with `FISHORA_SKIP_FRONTEND=1` |
| `Frontend dependencies missing` | `cd apps/frontend && pnpm install` |
| `PyTorch is not installed in .venv` | The `cv` extra was never installed. The script prints the exact two commands to run |
| `cannot see a CUDA device` | Torch is installed without CUDA support. Reinstall from the cu128 index |
| `Missing .venv` | No virtualenv found at `.venv`. The script accepts both `bin/` (POSIX) and `Scripts/` (Windows) layouts |
| Knowledge card returns 502 | `OPENCODE_GO_API_KEY` is blank or generation is unreachable. Identification and verification are unaffected |
| Knowledge card returns 409 | The prediction is still `pending`. Verify the species first |
| `EADDRINUSE` on startup | A previous run is still bound. Override the port, or stop the old process |
| Frontend loads but every request fails | Check the `API base` line the run script prints. It is compiled into the browser bundle, so it must be reachable *from the browser*, never an internal hostname |

## Repository Layout

```text
apps/
  frontend/       Next.js 16 app: App Router, Tailwind v4, design tokens
  main_api/       FastAPI: identification, verification, RAG knowledge cards
  cv_service/     FastAPI: DINOv3 inference
  common/         Shared image validation
ai/training/      PRD.md, the product requirements document
docs/plans/       Implementation plans
scripts/          run_local.sh, taxonomy seeding, corpus pipeline
tests/            pytest suites: unit, main_api, cv_service, integration
DESIGN.md         Design system, component specs, mobile-first mandate
```
