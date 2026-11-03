#!/usr/bin/env python3
"""Run a command and preserve its output, exit status, duration and peak RSS."""

import argparse
import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start = time.monotonic()
    with args.output.open("x") as stream:
        result = subprocess.run(
            command, cwd=args.cwd, stdout=stream, stderr=subprocess.STDOUT
        )
    metadata = {
        "command": command,
        "cwd": str(args.cwd.resolve()),
        "started_utc": started,
        "duration_seconds": round(time.monotonic() - start, 3),
        "exit_code": result.returncode,
        "max_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "rss_note": (
            "Linux maximum child RSS; not aggregate simultaneous cluster memory"
        ),
        "environment": {
            key: os.environ[key]
            for key in (
                "JAVA_HOME",
                "JAVA_TOOL_OPTIONS",
                "ZK_SERVER_HEAP",
                "LEGOLAS_JAVA_OPTS",
            )
            if key in os.environ
        },
    }
    args.output.with_suffix(".meta.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    print(json.dumps(metadata, indent=2), flush=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
