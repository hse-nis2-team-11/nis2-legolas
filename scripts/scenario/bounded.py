"""Run a foreground hook with a time limit and stop its entire process group."""

import os
import signal
import subprocess
import sys


def run(command, seconds):
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        return 124
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


if __name__ == "__main__":
    sys.exit(run(sys.argv[2:], int(sys.argv[1])))
