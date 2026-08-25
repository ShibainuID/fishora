# Fishora

Fishora is a fish-identification backend that combines a DINOv3 image classifier with retrieval-augmented generation. The local runtime starts PostgreSQL in Docker and runs both FastAPI services from one Python environment.

## Prerequisites

- Python 3.11
- Docker with Docker Compose
- An NVIDIA GPU with a CUDA-compatible driver
- A model export containing `model_state_dict.pt`, `inference_config.json`, and `inference.py`

The default model export path is `ai/results/fishora_dinov3_large_frozen/export`.

## Local Setup

Create one virtual environment and install CUDA-enabled PyTorch before installing Fishora:

```bash
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install -e '.[cv,dev]'
```

Verify that PyTorch can access the GPU:

```bash
.venv/bin/python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

Cache the embedding model once while internet access is available. Runtime loading is offline-only.

```bash
.venv/bin/python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("intfloat/multilingual-e5-base")'
```

Configuration defaults are ready for local use. Create `.env` only when you need to override them or provide an OpenCode Go API key for generated fish cards:

```bash
cp .env.example .env
```

Set `OPENCODE_GO_API_KEY` in `.env`. The researcher, four domain experts, critic, and writer share one OpenCode Go client configured with `FISHORA_OPENCODE_GO_MODEL=gpt-5.6-luna`.

Never commit `.env` or API keys.

## Run Locally

Start the complete local runtime:

```bash
bash scripts/run_local.sh
```

The script verifies CUDA, starts PostgreSQL, applies migrations, seeds taxonomy data, and launches both services. DINOv3 runs on CUDA while multilingual E5 embeddings run on CPU.

| Service | URL |
| --- | --- |
| Main API | `http://localhost:8000` |
| Interactive API docs | `http://localhost:8000/docs` |
| CV service | `http://localhost:8001` |

Stop the runtime with `Ctrl+C`. The script stops both API processes; PostgreSQL remains available in Docker. Stop it separately when needed:

```bash
docker compose down
```

## Verify the Services

Check the CV service from another terminal:

```bash
curl -fsS http://localhost:8001/health
```

A healthy response reports `status` and `model_version`.

## Run Tests

Run the tests that do not require PostgreSQL or real model artifacts:

```bash
.venv/bin/python -m pytest -m "not integration and not real_artifact" -q
```

For integration tests, start PostgreSQL and apply migrations first:

```bash
docker compose up -d db
export FISHORA_DATABASE_URL=postgresql+psycopg://fishora:fishora@localhost:55432/fishora
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest -m integration -q
```
