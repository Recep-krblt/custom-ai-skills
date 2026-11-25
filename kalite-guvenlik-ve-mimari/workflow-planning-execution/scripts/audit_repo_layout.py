#!/usr/bin/env python3
"""Read-Only Repository Layout & Clutter Auditor.

Inspects directory structure, root clutter, temporary/backup artifacts, empty
directories, excessive nesting depth, and large files across a project without
modifying any files. Reports tracked vs. untracked status when inside a Git repo.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".astro",
    "dist",
    "build",
    "out",
    "target",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".superpowers",
    ".site-builds",
}

ALLOWED_ROOT_EXACT = {
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".env.production.example",
    ".gitattributes",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".repo-map.md",
    ".repo-map.cache.json",
    "agents.md",
    "cargo.lock",
    "cargo.toml",
    "claude.md",
    "code_of_conduct.md",
    "contributing.md",
    "dockerfile",
    "embed.go",
    "gemini.md",
    "go.mod",
    "go.sum",
    "license",
    "license.md",
    "makefile",
    "main.go",
    "notice",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "readme.md",
    "requirements.txt",
    "security.md",
    "third_party_notices.md",
    "tsconfig.json",
    "uv.lock",
}

ALLOWED_ROOT_PREFIXES = (
    ".env",
    "readme",
    "license",
    "docker-compose",
    "dockerfile",
    "tsconfig.",
)

CRUFT_SUFFIXES = {".bak", ".orig", ".tmp", ".old", ".swp", ".swo", ".log", ".dmp"}
CRUFT_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
ROOT_CLUTTER_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".bak",
    ".tmp",
    ".csv",
    ".zip",
    ".tar",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".html",
    ".json",
}


def get_git_tracked(root: Path) -> set[str] | None:
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return None
        return {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}
    except OSError:
        return None


def is_root_allowed(name: str) -> bool:
    low = name.lower()
    if low in ALLOWED_ROOT_EXACT:
        return True
    if any(low.startswith(pref) for pref in ALLOWED_ROOT_PREFIXES):
        return True
    return False


def audit_repo(root: Path, depth_threshold: int, large_mb: float) -> dict:
    tracked = get_git_tracked(root)
    top_counts: dict[str, int] = defaultdict(int)
    top_bytes: dict[str, int] = defaultdict(int)

    root_clutter: list[dict] = []
    temp_cruft: list[dict] = []
    empty_dirs: list[str] = []
    deep_files: list[dict] = []
    large_files: list[dict] = []

    large_limit = int(large_mb * 1024 * 1024)

    def tag_tracked(rel: str) -> str:
        if tracked is None:
            return "unknown"
        return "tracked" if rel in tracked else "untracked"

    # Walk directory tree respecting SKIP_DIRS
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            entries = sorted(cur.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue

        visible_children = [e for e in entries if not (e.is_dir() and e.name in SKIP_DIRS)]
        if cur != root and not visible_children:
            empty_dirs.append(str(cur.relative_to(root)).replace("\\", "/"))

        for entry in entries:
            name = entry.name
            if entry.is_dir():
                if name in SKIP_DIRS:
                    continue
                stack.append(entry)
                continue

            if not entry.is_file():
                continue

            rel = str(entry.relative_to(root)).replace("\\", "/")
            parts = entry.relative_to(root).parts
            top_key = "(root)" if len(parts) == 1 else parts[0]
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0

            top_counts[top_key] += 1
            top_bytes[top_key] += size

            low_name = name.lower()
            suffix = entry.suffix.lower()

            if len(parts) == 1 and not is_root_allowed(name):
                if suffix in ROOT_CLUTTER_SUFFIXES or low_name in CRUFT_NAMES or low_name.endswith("~"):
                    root_clutter.append({"path": rel, "bytes": size, "git": tag_tracked(rel)})

            if suffix in CRUFT_SUFFIXES or low_name in CRUFT_NAMES or low_name.endswith("~"):
                temp_cruft.append({"path": rel, "bytes": size, "git": tag_tracked(rel)})

            if len(parts) > depth_threshold:
                deep_files.append({"path": rel, "depth": len(parts)})

            if size >= large_limit:
                large_files.append({"path": rel, "mb": round(size / (1024 * 1024), 2), "git": tag_tracked(rel)})

    large_files.sort(key=lambda x: x["mb"], reverse=True)
    deep_files.sort(key=lambda x: x["depth"], reverse=True)
    empty_dirs.sort()

    summary = [
        {
            "dir": k,
            "files": top_counts[k],
            "kb": round(top_bytes[k] / 1024, 1),
        }
        for k in sorted(top_counts, key=lambda d: top_counts[d], reverse=True)
    ]

    return {
        "root": str(root),
        "git_detected": tracked is not None,
        "top_dirs": summary,
        "root_clutter": root_clutter,
        "temp_cruft": temp_cruft,
        "empty_dirs": empty_dirs,
        "deep_files": deep_files,
        "large_files": large_files,
    }


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Read-only project directory structure & clutter audit helper."
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository or directory root to audit")
    parser.add_argument("--depth-threshold", type=int, default=5, help="Flag files nested deeper than N levels")
    parser.add_argument("--large-mb", type=float, default=1.0, help="Flag files >= N MB (default: 1.0)")
    parser.add_argument("--limit", type=int, default=15, help="Max items per section in text output (default: 15)")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.is_dir():
        print(f"[Error] Directory not found: {target}", file=sys.stderr)
        return 2

    report = audit_repo(target, depth_threshold=args.depth_threshold, large_mb=args.large_mb)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(f"Repo Layout Audit: {report['root']} (git={'yes' if report['git_detected'] else 'no'})")
    print("\n[Top-Level Footprint]")
    for item in report["top_dirs"][: args.limit]:
        print(f"  - {item['dir']}: {item['files']} files ({item['kb']} KB)")

    sections = [
        ("root_clutter", "Root Clutter Candidates", lambda x: f"{x['path']} ({x['bytes']} B, {x['git']})"),
        ("temp_cruft", "Temp / Log / OS Cruft", lambda x: f"{x['path']} ({x['git']})"),
        ("empty_dirs", "Empty Directories", lambda x: x),
        ("deep_files", f"Deeply Nested (>{args.depth_threshold} levels)", lambda x: f"{x['path']} (depth={x['depth']})"),
        ("large_files", f"Large Files (>={args.large_mb} MB)", lambda x: f"{x['path']} ({x['mb']} MB, {x['git']})"),
    ]
    for key, title, fmt in sections:
        items = report[key]
        print(f"\n[{title}] ({len(items)})")
        for it in items[: args.limit]:
            print(f"  - {fmt(it)}")
        if len(items) > args.limit:
            print(f"  ... ({len(items) - args.limit} more omitted; raise --limit)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
