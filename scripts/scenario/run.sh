#!/usr/bin/env bash
# Run inside a fresh checkpoint image; /results and the two hooks are mounted by the caller.
set -euo pipefail
cd /opt/nis2-legolas
if [[ $# != 5 ]]; then
    echo 'Usage: run.sh /results/NEW_DIR WRITER CHECKER None|Random|RoundRobinStateOp PHASE_TIMEOUT_SECONDS' >&2
    exit 2
fi
case "$4" in None|Random|RoundRobinStateOp) ;; *) exit 2 ;; esac
legolas=$PWD/.local/legolas
workspace=$legolas/workspace/legolas-zk
[[ ! -e "$workspace" && ! -e "$1" ]] || { echo 'Use a fresh container and result directory' >&2; exit 1; }
export JAVA_TOOL_OPTIONS='-Xmx512m -XX:ActiveProcessorCount=2 -Djava.rmi.server.hostname=127.0.0.1 -Djava.net.preferIPv4Stack=true -Duser.name=legolas'
export ZK_SERVER_HEAP=512
(cd "$legolas" && bash scripts/experiment/setup-legolas-zookeeper.sh ../zookeeper 3.6.2)
for cfg in "$workspace"/conf-*/zoo.cfg; do
    printf '\nclientPortAddress=127.0.0.1\nadmin.enableServer=false\n' >> "$cfg"
done
exec java -cp "scenario-classes:$(cat scenario-classpath)" Trial "$workspace/legolas-zk.properties" "$@"
