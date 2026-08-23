#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  printf 'Missing .venv. Follow artifacts/docs/fish-identification-rag-runbook.md first.\n' >&2
  exit 1
fi

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

export FISHORA_CV_EXPORT_DIR="${FISHORA_CV_EXPORT_DIR:-ai/results/fishora_dinov3_large_frozen/export}"
export FISHORA_CV_MODEL_VERSION="${FISHORA_CV_MODEL_VERSION:-fishora-dinov3-export}"
export FISHORA_CV_DEVICE="${FISHORA_CV_DEVICE:-cuda}"
export FISHORA_EMBEDDING_DEVICE="${FISHORA_EMBEDDING_DEVICE:-cpu}"
export FISHORA_CV_SERVICE_URL="${FISHORA_CV_SERVICE_URL:-http://localhost:8001}"

.venv/bin/python -c 'import torch; assert torch.cuda.is_available(), "CUDA is unavailable in .venv"'
docker compose up -d db

export FISHORA_DATABASE_URL="${FISHORA_DATABASE_URL:-postgresql+psycopg://fishora:fishora@localhost:55432/fishora}"
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_taxonomy

cleanup() {
  kill "$MAIN_PID" "$CV_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/uvicorn apps.cv_service.main:app --host 0.0.0.0 --port 8001 &
CV_PID=$!
.venv/bin/uvicorn apps.main_api.main:app --host 0.0.0.0 --port 8000 &
MAIN_PID=$!

wait -n "$CV_PID" "$MAIN_PID"
