#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FRONTEND_DIR="$ROOT_DIR/apps/frontend"

# Virtualenvs put the interpreter in bin/ on POSIX and Scripts/ on Windows.
# Detect it rather than assuming, so the same script works from Git Bash.
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif [[ -x .venv/Scripts/python.exe ]]; then
  PY=".venv/Scripts/python.exe"
else
  printf 'Missing .venv. Follow the Setup section in README.md first.\n' >&2
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

# Ports for the three HTTP surfaces. The frontend keeps Next.js's own default.
export FISHORA_MAIN_API_PORT="${FISHORA_MAIN_API_PORT:-8000}"
export FISHORA_CV_SERVICE_PORT="${FISHORA_CV_SERVICE_PORT:-8001}"
export FISHORA_FRONTEND_PORT="${FISHORA_FRONTEND_PORT:-3000}"

export FISHORA_CV_SERVICE_URL="${FISHORA_CV_SERVICE_URL:-http://localhost:${FISHORA_CV_SERVICE_PORT}}"

# The browser calls the API directly, so these two must agree or every request
# fails: the frontend needs the API's address, and the API needs the frontend's
# origin in its CORS allow-list. Deriving both from the ports above keeps them
# in step when someone changes a port to dodge a conflict.
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${FISHORA_MAIN_API_PORT}}"
export FISHORA_CORS_ALLOW_ORIGINS="${FISHORA_CORS_ALLOW_ORIGINS:-http://localhost:${FISHORA_FRONTEND_PORT},http://127.0.0.1:${FISHORA_FRONTEND_PORT}}"

# The frontend is optional: the backend and CV service are useful on their own,
# and a machine without Node should still be able to run them. Set
# FISHORA_SKIP_FRONTEND=1 to skip it deliberately.
RUN_FRONTEND=1
if [[ "${FISHORA_SKIP_FRONTEND:-0}" == "1" ]]; then
  RUN_FRONTEND=0
elif ! command -v pnpm >/dev/null 2>&1; then
  printf 'pnpm not found: starting backend and CV service only. Install pnpm to run the frontend.\n' >&2
  RUN_FRONTEND=0
elif [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  printf 'Frontend dependencies missing. Run: (cd apps/frontend && pnpm install)\n' >&2
  RUN_FRONTEND=0
fi

# Distinguish "torch is not installed" from "torch cannot see the GPU": they
# have different fixes, and a bare traceback sends people to the wrong one.
if ! "$PY" -c 'import torch' 2>/dev/null; then
  printf 'PyTorch is not installed in .venv. Install the CV extra:\n' >&2
  printf "  %s -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128\n" "$PY" >&2
  printf "  %s -m pip install -e '.[cv,dev]'\n" "$PY" >&2
  exit 1
fi
if ! "$PY" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)'; then
  printf 'PyTorch is installed but cannot see a CUDA device. Reinstall from the cu128 index.\n' >&2
  exit 1
fi
docker compose up -d db

export FISHORA_DATABASE_URL="${FISHORA_DATABASE_URL:-postgresql+psycopg://fishora:fishora@localhost:55432/fishora}"
"$PY" -m alembic upgrade head
"$PY" -m scripts.seed_taxonomy

cleanup() {
  # ${VAR:-} guards a pid that was never assigned: the trap is installed before
  # the services start, and set -u would otherwise abort the handler itself.
  for pid in "${FRONTEND_PID:-}" "${MAIN_PID:-}" "${CV_PID:-}"; do
    [[ -n "$pid" ]] || continue
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

"$PY" -m uvicorn apps.cv_service.main:app --host 0.0.0.0 --port "$FISHORA_CV_SERVICE_PORT" &
CV_PID=$!
"$PY" -m uvicorn apps.main_api.main:app --host 0.0.0.0 --port "$FISHORA_MAIN_API_PORT" &
MAIN_PID=$!

if (( RUN_FRONTEND )); then
  # --hostname 0.0.0.0 exposes the dev server on the LAN, which is how you open
  # the operator flow on a real phone. DESIGN.md treats mobile as the primary
  # target, and that is not verifiable from a desktop browser alone.
  (cd "$FRONTEND_DIR" && pnpm dev --port "$FISHORA_FRONTEND_PORT" --hostname 0.0.0.0) &
  FRONTEND_PID=$!
fi

printf '\n  Main API    http://localhost:%s  (docs at /docs)\n' "$FISHORA_MAIN_API_PORT"
printf '  CV service  http://localhost:%s\n' "$FISHORA_CV_SERVICE_PORT"
if (( RUN_FRONTEND )); then
  printf '  Frontend    http://localhost:%s\n' "$FISHORA_FRONTEND_PORT"
  printf '  API base    %s\n' "$NEXT_PUBLIC_API_BASE_URL"
  printf '  CORS allow  %s\n\n' "$FISHORA_CORS_ALLOW_ORIGINS"
else
  printf '  Frontend    not started\n\n'
fi

# Exit as soon as any service dies, so a crash is visible immediately instead
# of leaving a half-running stack that still looks healthy.
wait -n "$CV_PID" "$MAIN_PID" ${FRONTEND_PID:+"$FRONTEND_PID"}
