#!/usr/bin/env python3
"""Bisection script to identify which test file creates an unwanted file or state (test pollution).

Adapted from obra/superpowers `find-polluter.sh` for cross-platform Windows/POSIX usage.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path


def build_command(cmd_template: str | None, test_file: str) -> str:
    if cmd_template:
        if "{test}" in cmd_template:
            return cmd_template.replace("{test}", f'"{test_file}"')
        return f'{cmd_template} "{test_file}"'
    if test_file.endswith(".py"):
        return f'pytest "{test_file}"'
    return f'npm test -- "{test_file}"'


def artifact_matches(pattern: str, cwd: Path) -> list[Path]:
    candidate = Path(pattern)
    if candidate.is_absolute():
        return [Path(p) for p in glob.glob(str(candidate), recursive=True)]
    return [Path(p) for p in glob.glob(str(cwd / pattern), recursive=True)]


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Find which test file creates an unwanted file or directory (test pollution).",
        epilog=(
            "Examples:\n"
            '  python find_polluter.py .git "src/**/*.test.ts"\n'
            '  python find_polluter.py "*.tmp" "tests/test_*.py" --cmd "pytest -q {test}"\n'
            "Exit codes: 0 = no polluter found, 1 = polluter identified, 2 = precondition/usage error."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("artifact", help="Relative path or glob pattern of the unwanted artifact to watch for.")
    parser.add_argument("test_glob", help="Glob pattern matching test files (e.g. 'tests/**/*.test.ts').")
    parser.add_argument(
        "--cmd",
        "-c",
        default=None,
        help="Test command template. Use {test} for file path placeholder (default: pytest for .py, npm test otherwise).",
    )
    parser.add_argument("--cwd", default=".", help="Project working directory (default: current directory).")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print failing/stdout tail for each run.")
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(f"[Error] Working directory not found: {cwd}", file=sys.stderr)
        return 2

    if artifact_matches(args.artifact, cwd):
        print(
            f"[Error] Artifact '{args.artifact}' already exists in {cwd} before tests ran. Clean it up first.",
            file=sys.stderr,
        )
        return 2

    test_files = sorted(glob.glob(str(cwd / args.test_glob), recursive=True))
    test_files = [os.path.relpath(f, cwd) for f in test_files if Path(f).is_file()]

    if not test_files:
        print(f"[Error] No test files matched '{args.test_glob}' under {cwd}", file=sys.stderr)
        return 2

    print(f"Searching {len(test_files)} test file(s) for polluter creating '{args.artifact}'...")

    for idx, test_file in enumerate(test_files, start=1):
        print(f"[{idx}/{len(test_files)}] Testing: {test_file}")
        cmd = build_command(args.cmd, test_file)
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            shell=True,
            stdout=subprocess.PIPE if not args.verbose else None,
            stderr=subprocess.STDOUT if not args.verbose else None,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        found = artifact_matches(args.artifact, cwd)
        if found:
            print("\n=== POLLUTER FOUND ===")
            print(f"Test file: {test_file}")
            print(f"Created  : {', '.join(str(p) for p in found)}")
            print(f"Command  : {cmd} (exit={proc.returncode})")
            return 1

    print("\nNo polluter found across matched test files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
