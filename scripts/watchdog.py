"""Run a long command with heartbeat, timeout, and safe process termination.

Usage (Windows cmd):
  python scripts/watchdog.py --timeout 300 --heartbeat 15 -- python -m pytest runtime/tests -q
  python scripts/watchdog.py --timeout 300 -- npm test

The watchdog is deliberately conservative: it never restarts a failed command.
On timeout it terminates the child process tree and reports a clear BLOCKED result.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

STATE_FILE = Path("runtime_data/watchdog_last_run.json")


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def write_state(command: list[str], status: str, detail: str, started: float, ended: float | None = None) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    elapsed = round((ended or time.monotonic()) - started, 1)
    payload = {
        "timestamp": now(),
        "status": status,
        "elapsed_seconds": elapsed,
        "detail": detail,
        "command": command,
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def stop_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchdog for long-running commands")
    parser.add_argument("--timeout", type=float, default=300.0, help="maximum runtime in seconds")
    parser.add_argument("--heartbeat", type=float, default=15.0, help="status interval in seconds")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command is required after --")

    started = time.monotonic()
    print(f"[WATCHDOG] START {now()} | timeout={args.timeout:.0f}s | heartbeat={args.heartbeat:.0f}s", flush=True)
    print(f"[WATCHDOG] CMD {' '.join(command)}", flush=True)
    write_state(command, "RUNNING", "command is running", started)

    try:
        process = subprocess.Popen(
            command,
            stdout=None,
            stderr=None,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
        )
    except OSError as exc:
        write_state(command, "BLOCKED", f"could not start: {exc}", started, time.monotonic())
        print(f"[WATCHDOG] BLOCKED: could not start: {exc}", flush=True)
        return 2

    stop_event = threading.Event()

    def heartbeat() -> None:
        while not stop_event.wait(args.heartbeat):
            elapsed = time.monotonic() - started
            remaining = max(0.0, args.timeout - elapsed)
            print(f"[WATCHDOG] RUNNING elapsed={elapsed:.0f}s remaining={remaining:.0f}s", flush=True)
            write_state(command, "RUNNING", "heartbeat; command is still running", started)

    thread = threading.Thread(target=heartbeat, name="watchdog-heartbeat", daemon=True)
    thread.start()
    try:
        return_code = process.wait(timeout=args.timeout)
        elapsed = time.monotonic() - started
        status = "PASS" if return_code == 0 else "FAIL"
        write_state(command, status, f"process exited with code {return_code}", started, time.monotonic())
        print(f"[WATCHDOG] {status} exit={return_code} elapsed={elapsed:.0f}s", flush=True)
        return return_code
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(f"[WATCHDOG] TIMEOUT after {elapsed:.0f}s; terminating process tree PID={process.pid}", flush=True)
        try:
            stop_tree(process)
        except Exception as exc:
            detail = f"timeout; termination warning: {exc}"
        else:
            detail = "timeout; process tree terminated"
        write_state(command, "BLOCKED", detail, started, time.monotonic())
        print(f"[WATCHDOG] BLOCKED: {detail}", flush=True)
        return 124
    except KeyboardInterrupt:
        print("[WATCHDOG] INTERRUPTED; terminating process tree", flush=True)
        stop_tree(process)
        write_state(command, "BLOCKED", "interrupted by user", started, time.monotonic())
        return 130
    finally:
        stop_event.set()
        thread.join(timeout=2)


if __name__ == "__main__":
    sys.exit(main())