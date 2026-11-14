#!/usr/bin/env python3
"""Cross-platform command watchdog and timeout runner.

Prevents agents and test suites from hanging indefinitely due to:
- Test runners defaulting to interactive watch mode (Vitest, Jest)
- Unclosed database/HTTP server connections keeping the event loop alive
- Infinite loops or hanging async promises
- Dangling background child process trees
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run any test or shell command with a strict timeout and automatic process-tree cleanup.",
        epilog=(
            "Examples:\n"
            '  python run_with_timeout.py --timeout 20 "npx vitest run"\n'
            '  python run_with_timeout.py --timeout 15 "pytest -q"\n'
            '  python run_with_timeout.py --timeout 30 -- npm test -- --run\n'
            "Exit codes: 0 = passed, >0 = command error, 124 = timed out & killed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=30.0,
        help="Maximum execution time in seconds before process tree is forcibly killed (default: 30.0s).",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Working directory to execute command in (default: current directory).",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command line to execute. Use '--' separator before command if passing flags.",
    )

    args = parser.parse_args()

    cmd_args = args.command
    if cmd_args and cmd_args[0] == "--":
        cmd_args = cmd_args[1:]

    if not cmd_args:
        print("[Error] No command specified. Run with --help for usage.", file=sys.stderr)
        return 2

    # If passed as single string e.g. "pytest -q", keep it as string; if list, join or keep shell
    cmd_str = " ".join(cmd_args) if len(cmd_args) > 1 else cmd_args[0]

    env = os.environ.copy()
    # Enforce non-interactive CI mode to disable watch modes across Jest, Vitest, etc.
    env["CI"] = "1"
    env["CONTINUOUS_INTEGRATION"] = "1"
    env["TERM"] = "dumb"

    start_time = time.time()
    timed_out = False

    # Start process with its own process group on POSIX
    kwargs: dict[str, object] = {
        "cwd": args.cwd,
        "env": env,
        "shell": True,
    }
    if sys.platform != "win32":
        kwargs["preexec_fn"] = os.setsid

    proc = subprocess.Popen(cmd_str, **kwargs)

    try:
        proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        elapsed = time.time() - start_time
        print(
            f"\n[TIMEOUT ERROR] Command exceeded {args.timeout}s limit (elapsed {elapsed:.1f}s) and was terminated.",
            file=sys.stderr,
        )
        print(
            "[DIAGNOSTIC] Possible causes: (1) Test runner running in watch mode; (2) Unclosed DB/server sockets; (3) Infinite loop or unresolved Promise.",
            file=sys.stderr,
        )

        if sys.platform == "win32":
            # Force-kill entire child process tree on Windows
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Kill process group on POSIX
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                proc.kill()

        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    if timed_out:
        return 124

    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
