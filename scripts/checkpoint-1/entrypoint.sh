#!/usr/bin/env bash
set -euo pipefail
cd /opt/nis2-legolas
if [[ ${1:-} == bash ]]; then
    exec "$@"
fi
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    exec python3 scripts/checkpoint-1/smoke_run.py --help
fi
run_name=${1:?Specify a unique result name and --policy None/Random/RoundRobinStateOp}
if [[ ! "$run_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]]; then
    echo 'Invalid result name.' >&2
    exit 2
fi
result_dir="$EVIDENCE_DIR/$run_name"
if [[ -e "$result_dir" ]]; then
    echo "Refusing to overwrite $result_dir" >&2
    exit 2
fi
run_status=0
python3 scripts/checkpoint-1/smoke_run.py "$@" || run_status=$?
if [[ -d "$result_dir" && -f "$result_dir/console.meta.json" ]]; then
    cp -R build-evidence "$result_dir/image-build"
    {
        cat /etc/os-release
        uname -srmo
        id
        java -version
        mvn -version
    } > "$result_dir/container-environment.txt" 2>&1
fi
if (( run_status != 0 )); then
    exit "$run_status"
fi
python3 scripts/checkpoint-1/summarize_smoke.py "$result_dir"
