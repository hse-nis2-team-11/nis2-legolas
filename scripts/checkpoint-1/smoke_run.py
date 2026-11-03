#!/usr/bin/env python3
"""Run the upstream CreateReadWrite smoke scenario and archive all evidence."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("name", help="unique evidence directory name")
parser.add_argument(
    "--policy", choices=["None", "Random", "RoundRobinStateOp"], required=True
)
parser.add_argument("--trials", type=int, default=3)
parser.add_argument("--timeout-ms", type=int, default=30000)
parser.add_argument("--warmup-ms", type=int, default=3000)
args = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.name) or args.trials < 1:
    parser.error("invalid name or trial count")
if not os.environ.get("JAVA_HOME") or not os.environ.get("EVIDENCE_DIR"):
    parser.error("run through scripts/checkpoint-1/docker.sh")
evidence_root = Path(os.environ["EVIDENCE_DIR"])
output = evidence_root / args.name
if output.exists():
    parser.error(f"refusing to overwrite {output}")
legolas = root / ".local/legolas"
workspace = legolas / "workspace/legolas-zk"
if workspace.exists():
    parser.error("the workspace already exists; use a fresh container for each run")
env = os.environ.copy()
env["PATH"] = env["JAVA_HOME"] + "/bin:" + env["PATH"]
# Match the image's USER variable even when Docker runs with a numeric host UID.
env["JAVA_TOOL_OPTIONS"] = (
    "-Xmx512m -XX:ActiveProcessorCount=2 "
    "-Djava.rmi.server.hostname=127.0.0.1 "
    "-Djava.net.preferIPv4Stack=true -Duser.name=legolas"
)
env["ZK_SERVER_HEAP"] = "512"
output.mkdir(parents=True)
with (output / "setup.log").open("w") as stream:
    subprocess.run(
        [
            "bash",
            "scripts/experiment/setup-legolas-zookeeper.sh",
            "../zookeeper",
            "3.6.2",
        ],
        cwd=legolas,
        env=env,
        stdout=stream,
        stderr=subprocess.STDOUT,
        check=True,
    )
props = workspace / "legolas-zk.properties"
text = props.read_text()
values = {
    "injectionPolicy": args.policy,
    "maxTrials": args.trials,
    "trialTimeout": args.timeout_ms,
    "warmupMillis": args.warmup_ms,
    "failTrialRetries": 0,
    "maxTotalRetries": 0,
}
for key, value in values.items():
    text, count = re.subn(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    if count != 1:
        raise RuntimeError(f"expected one {key} setting, found {count}")
props.write_text(text + "\nrecordStates=true\nrandomRate=100\n")
for i in (1, 2, 3):
    cfg = workspace / f"conf-{i}/zoo.cfg"
    cfg.write_text(
        cfg.read_text() + "\nclientPortAddress=127.0.0.1\nadmin.enableServer=false\n"
    )
    shutil.copy(cfg, output / f"zoo-{i}.cfg")
shutil.copy(props, output / props.name)
for name in ("client.sh", "server.sh"):
    shutil.copy(workspace / name, output / name)
timeout_seconds = args.trials * (args.timeout_ms // 1000 + 5) + 60
result = subprocess.run(
    [
        sys.executable,
        str(root / "scripts/run_logged.py"),
        "--output",
        str(output / "console.log"),
        "--cwd",
        str(legolas),
        "--",
        "timeout",
        "--kill-after=10s",
        f"{timeout_seconds}s",
        "bash",
        "scripts/experiment/start-legolas-zookeeper.sh",
    ],
    env=env,
)
if (workspace / "trials").exists():
    shutil.copytree(workspace / "trials", output / "trials")
log = legolas / "logs/legolas-orchestrator.log"
if log.exists():
    shutil.copy(log, output / "orchestrator.log")
print(f"Evidence saved in {output}", flush=True)
raise SystemExit(result.returncode)
