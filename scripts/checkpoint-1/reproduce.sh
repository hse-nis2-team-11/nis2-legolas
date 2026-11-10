#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

results_dir="${1:-.local/reproductions/checkpoint-1-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$results_dir"
export LEGOLAS_RESULTS_DIR="$(cd "$results_dir" && pwd)"

bash scripts/checkpoint-1/docker.sh run control --policy None
bash scripts/checkpoint-1/docker.sh run round-robin --policy RoundRobinStateOp
bash scripts/checkpoint-1/docker.sh run random --policy Random

printf '\nResults: %s\n' "$LEGOLAS_RESULTS_DIR"
