#!/usr/bin/env bash
# Build or run the isolated checkpoint-1 environment; only Docker is needed on host.
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_dir"
image_name=${LEGOLAS_IMAGE:-nis2-legolas:checkpoint-1}
stage=${1:-help}
case "$stage" in
build)
    shift
    docker build --platform linux/amd64 --progress=plain \
        --network "${DOCKER_BUILD_NETWORK:-default}" -t "$image_name" "$@" .
    ;;
run)
    shift
    results_dir=${LEGOLAS_RESULTS_DIR:-$repo_dir/evidence/checkpoint-1/runs}
    mkdir -p "$results_dir"
    results_dir=$(cd "$results_dir" && pwd)
    exec docker run --rm --init --platform linux/amd64 \
        --network none --hostname legolas --add-host legolas:127.0.0.1 \
        --cpus "${LEGOLAS_CPUS:-4}" --memory "${LEGOLAS_MEMORY:-8g}" \
        --user "$(id -u):$(id -g)" \
        --mount "type=bind,source=$results_dir,target=/results" \
        "$image_name" "$@"
    ;;
*)
    cat <<'EOF'
Usage:
  bash scripts/checkpoint-1/docker.sh build
  bash scripts/checkpoint-1/docker.sh run control-repeat --policy None
  bash scripts/checkpoint-1/docker.sh run rr-repeat --policy RoundRobinStateOp
  bash scripts/checkpoint-1/docker.sh run random-repeat --policy Random

Optional environment variables:
  DOCKER_BUILD_NETWORK=host   if Docker bridge DNS does not work on this host
  LEGOLAS_IMAGE              image tag (default nis2-legolas:checkpoint-1)
  LEGOLAS_RESULTS_DIR        host directory for output
  LEGOLAS_CPUS=4             runtime CPU quota
  LEGOLAS_MEMORY=8g          runtime memory limit
Each run needs a new result name. No server ports or Docker socket are exposed.
EOF
    ;;
esac
