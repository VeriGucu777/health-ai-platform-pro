Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
docker compose -f docker-compose.embedding-test.yml build embedding-tests
docker compose -f docker-compose.embedding-test.yml run --rm embedding-tests
# Runs scripts/run_rag_v1_closure_tests.sh (two pytest processes — see README)
