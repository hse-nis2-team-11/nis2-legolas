#!/usr/bin/env python3
"""Summarize the upstream workload, not the future data-preservation checker."""

import argparse
import csv
import gzip
import json
from pathlib import Path
import re


def read_text(path):
    if not path.exists():
        path = path.with_name(path.name + ".gz")
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode()
    return path.read_text()


def summarize(directory):
    props = dict(
        line.split("=", 1)
        for line in read_text(directory / "legolas-zk.properties").splitlines()
        if "=" in line and not line.startswith("#")
    )
    console = read_text(directory / "console.log")
    trials = []
    for trial in sorted((directory / "trials").iterdir(), key=lambda p: int(p.name)):
        tid = int(trial.name)
        lines = [line for line in console.splitlines() if f"[trial:{tid}]" in line]
        phase_results = {}
        for line in lines:
            match = re.search(r"Phase \d+ - (create|read|write)\s*:\[(.*?)\]", line)
            if match:
                phase_results[match[1]] = [
                    list(map(int, pair.split("/"))) for pair in match[2].split(", ")
                ]
        completed = {
            phase: sum(pair[0] for pair in pairs)
            for phase, pairs in phase_results.items()
        }
        finished = set(phase_results) == {"create", "read", "write"} and all(
            a == b for pairs in phase_results.values() for a, b in pairs
        )
        metadata = json.loads(read_text(trial / "orch.json"))
        events = csv.reader(read_text(trial / "orch.csv").splitlines())
        header = next(events)
        if header[:2] != ["event-id", "time"]:
            raise ValueError(
                "Unexpected upstream CSV header; recheck positional decoding"
            )
        # In revision 84278d313f98 RecordWriter.write() writes time THEN type,
        # while the header says event-id,time. ThreadInjectionEvent.getType()=5.
        event_counts = {}
        grants = []
        max_ns = 0
        states = set()
        for row in events:
            ns, event_type = int(row[0]), int(row[1])
            max_ns = max(max_ns, ns)
            event_counts[str(event_type)] = event_counts.get(str(event_type), 0) + 1
            if event_type in (3, 4, 5):
                states.add(tuple(row[2:6]))
            if event_type == 5:
                exception_id = int(row[11])
                grants.append(
                    {
                        "time_seconds": ns / 1e9,
                        "server_id": int(row[2]),
                        "state_machine": metadata["state_machines"][int(row[3])],
                        "state_method": metadata["ops"][int(row[4])],
                        "state_id": int(row[5]),
                        "operation": metadata["ops"][int(row[7])],
                        "delay": bool(int(row[10])),
                        "exception": (
                            metadata["events"][exception_id]
                            if exception_id >= 0
                            else None
                        ),
                        "injection_id": int(row[12]),
                    }
                )
        execution_evidence = []
        stacks = []
        for logfile in sorted(trial.glob("logs-*/*.out*")):
            for line in read_text(logfile).splitlines():
                if (
                    "LegolasAgent injecting exception " in line
                    or "LegolasAgent injecting delay" in line
                ):
                    execution_evidence.append(
                        {"file": str(logfile.relative_to(directory)), "line": line}
                    )
                if "the stack trace of injection " in line:
                    stacks.append(
                        {"file": str(logfile.relative_to(directory)), "line": line}
                    )
        start_line = next(
            (line for line in lines if f"starting trial {tid}" in line), None
        )
        trials.append(
            {
                "trial_id": tid,
                "started_local": start_line[:23] if start_line else None,
                "recorded_duration_seconds": round(max_ns / 1e9, 6),
                "phase_progress": phase_results,
                "completed_operations": completed,
                "workload_completed": finished,
                "event_counts": event_counts,
                "observed_state_tuples": len(states),
                "granted_injections": grants,
                "executed_injection_evidence": execution_evidence,
                "injection_stacks": stacks,
                "preservation_verdict": "not_checked",
            }
        )
    requested = int(props["maxTrials"])
    if len(trials) != requested:
        raise ValueError(f"Expected {requested} trials, found {len(trials)}")
    result = {
        "policy": props["injectionPolicy"],
        "trial_count": len(trials),
        "completed_workloads": sum(t["workload_completed"] for t in trials),
        "trials_with_granted_injection": sum(
            bool(t["granted_injections"]) for t in trials
        ),
        "trials_with_executed_injection": sum(
            bool(t["executed_injection_evidence"]) for t in trials
        ),
        "preservation_verdict": "not_checked",
        "note": (
            "Author workload progress is not a data-preservation verdict "
            "or a count of bugs."
        ),
        "trials": trials,
    }
    (directory / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    with (directory / "summary.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "trial_id",
                "recorded_duration_seconds",
                "create_ok",
                "read_ok",
                "write_ok",
                "workload_completed",
                "granted_injections",
                "executed_injections",
                "preservation_verdict",
            ]
        )
        for t in trials:
            writer.writerow(
                [
                    t["trial_id"],
                    t["recorded_duration_seconds"],
                    *[
                        t["completed_operations"].get(k, 0)
                        for k in ("create", "read", "write")
                    ],
                    t["workload_completed"],
                    len(t["granted_injections"]),
                    len(t["executed_injection_evidence"]),
                    "not_checked",
                ]
            )
    if props["injectionPolicy"] == "None" and result["completed_workloads"] != len(
        trials
    ):
        raise SystemExit("Control workload incomplete; see saved summary")
    if (
        result["trials_with_granted_injection"]
        != result["trials_with_executed_injection"]
    ):
        raise SystemExit(
            "Granted and executed injection counts differ; inspect evidence"
        )
    print(
        f"{directory.name}: {len(trials)} trials, "
        f"{result['completed_workloads']} completed workloads, "
        f"{result['trials_with_executed_injection']} trials with an executed injection"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    for directory in parser.parse_args().directories:
        summarize(directory)
