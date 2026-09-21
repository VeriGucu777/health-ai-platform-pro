#!/usr/bin/env sh
# Official RAG Clinical Retrieval v1 closure workflow (Linux/Docker).
# Two pytest processes: stage 1 avoids ONNX; stage 2 loads the model once per process.
set -eu

log_rss() {
  label=$1
  if [ -r /proc/self/status ]; then
    rss=$(awk '/VmRSS/ {print $2}' /proc/self/status)
    hwm=$(awk '/VmHWM/ {print $2}' /proc/self/status)
    echo "MEMORY_${label}_VmRSS_kB=${rss} VmHWM_kB=${hwm}"
  fi
}

log_rss "startup"

run_pytest_timed() {
  stage=$1
  shift
  if command -v /usr/bin/time >/dev/null 2>&1; then
    /usr/bin/time -f "${stage}_TIME max_rss_kb=%M exit=%x" "$@"
  else
    "$@"
  fi
}

echo "=== Stage 1/2: unit + API (no PostgreSQL integration, no ONNX embedding suite) ==="
run_pytest_timed STAGE1 pytest tests/ -q --tb=short -m "not integration"
log_rss "after_stage1"

echo "=== Stage 2/2: embedding runtime + live pgvector E2E ==="
run_pytest_timed STAGE2 pytest tests/integration/embedding -q --tb=short
log_rss "after_stage2"

echo "RAG_V1_CLOSURE=OK"
