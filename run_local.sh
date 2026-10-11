#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
DEFAULT_PYTHON="/opt/homebrew/anaconda3/envs/neural_env/bin/python"
[[ -x "$DEFAULT_PYTHON" ]] || DEFAULT_PYTHON="python3.10"
PYTHON_BIN="${DENTALHELPER_PYTHON:-$DEFAULT_PYTHON}"
API_PID=""
OLLAMA_PID=""

cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$OLLAMA_PID" ]] && kill "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -n "${YOLO_MODEL_PATH:-}" && ! -f "$YOLO_MODEL_PATH" ]]; then
  printf 'YOLO_MODEL_PATH указывает на отсутствующий файл: %s\n' "$YOLO_MODEL_PATH" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf 'Не найден %s. Установите Python 3.10 или задайте DENTALHELPER_PYTHON.\n' "$PYTHON_BIN" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import fastapi, openai, PIL, requests, torch, ultralytics, uvicorn' >/dev/null 2>&1; then
  printf 'Не установлены зависимости ML/API для %s. Выполните: %s -m pip install -r requirements.txt -r web_api/requirements.txt\n' "$PYTHON_BIN" "$PYTHON_BIN" >&2
  exit 1
fi

export YOLO_CONFIG_DIR="${TMPDIR:-/tmp}/dentalhelper-ultralytics"
mkdir -p "$YOLO_CONFIG_DIR"

if ! curl --fail --silent http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama serve >/tmp/dentalhelper-ollama.log 2>&1 &
  OLLAMA_PID=$!
  for _ in {1..20}; do
    curl --fail --silent http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! ollama list | rg -F "${OLLAMA_MODEL:-llama3.1:8b-instruct-q5_K_M}" >/dev/null; then
  printf 'Локальная модель %s не найдена. Сначала выполните: ollama pull %s\n' "${OLLAMA_MODEL:-llama3.1:8b-instruct-q5_K_M}" "${OLLAMA_MODEL:-llama3.1:8b-instruct-q5_K_M}" >&2
  exit 1
fi

cd "$PROJECT_DIR"
"$PYTHON_BIN" -m uvicorn web_api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

for _ in {1..20}; do
  curl --fail --silent http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 1
done

printf 'DentalHelper запущен локально: http://localhost:5173\n'
cd "$PROJECT_DIR/web"
npm run dev
