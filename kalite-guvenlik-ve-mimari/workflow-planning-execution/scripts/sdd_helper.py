#!/usr/bin/env python3
"""Cross-platform SDD (Subagent-Driven Development) Helper CLI.

Handles workspace discovery, task brief extraction from plan markdown files,
review diff package generation, and ledger tracking. Works across Windows PowerShell and POSIX.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_repo_root(start_dir: Path | None = None) -> Path:
    cwd = (start_dir or Path.cwd()).resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except OSError as exc:
        raise RuntimeError(f"Unable to run git in '{cwd}': {exc}") from exc
    raise RuntimeError(
        f"'{cwd}' is not inside a Git repository. Pass -C <repo-dir> or run 'git init' with an initial commit first."
    )


def get_plan_slug(plan_path: Path) -> str:
    stem = plan_path.stem
    clean = re.sub(r"[^a-zA-Z0-9_\-]+", "-", stem).strip("-").lower()
    return clean or "plan"


def get_sdd_workspace(plan_path: Path, repo_root: Path | None = None) -> Path:
    root = get_repo_root(repo_root or plan_path.parent)
    slug = get_plan_slug(plan_path)
    workspace = root / ".superpowers" / "sdd" / slug
    workspace.mkdir(parents=True, exist_ok=True)

    # Ensure .gitignore inside .superpowers/sdd so plans never commit scratch artifacts
    sdd_parent = root / ".superpowers" / "sdd"
    gitignore = sdd_parent / ".gitignore"
    if not gitignore.exists():
        try:
            gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")
        except Exception:
            pass

    return workspace.resolve()


def extract_task_brief(
    plan_path: Path, task_id: str, out_path: Path | None = None, repo_root: Path | None = None
) -> Path:
    if not plan_path.is_file():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    text = plan_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    task_header_re = re.compile(r"^(#{1,4})\s+Task\s+([0-9A-Za-z_.\-]+)(?:\s*[:\-–—]\s*(.*))?$", re.IGNORECASE)

    target_task = str(task_id).strip().lower()
    start_idx = None
    target_depth = None

    for idx, line in enumerate(lines):
        m = task_header_re.match(line.strip())
        if m:
            heading_hashes, found_id, _ = m.groups()
            if found_id.strip().lower() == target_task:
                start_idx = idx
                target_depth = len(heading_hashes)
                break

    if start_idx is None:
        # Fallback: search for headings containing "Task <id>" anywhere
        fallback_re = re.compile(rf"^(#{{1,4}})\s+.*Task\s+{re.escape(target_task)}\b", re.IGNORECASE)
        for idx, line in enumerate(lines):
            m = fallback_re.match(line.strip())
            if m:
                start_idx = idx
                target_depth = len(m.group(1))
                break

    if start_idx is None or target_depth is None:
        raise ValueError(f"Task '{task_id}' not found in plan {plan_path}")

    # Extract lines until next task header at same or higher level
    extracted = [lines[start_idx]]
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        m = task_header_re.match(line.strip())
        if m and len(m.group(1)) <= target_depth:
            break
        extracted.append(line)

    content = "\n".join(extracted).strip() + "\n"

    if not out_path:
        ws = get_sdd_workspace(plan_path, repo_root=repo_root)
        out_path = ws / f"task-{target_task}-brief.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_review_package(base_sha: str, head_sha: str, out_path: Path | None = None, repo_root: Path | None = None) -> Path:
    root = get_repo_root(repo_root)

    def run_git(args: list[str], required: bool = False) -> str:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if required and proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed in '{root}': {proc.stderr.strip()}")
        return proc.stdout.strip()

    run_git(["rev-parse", "--verify", f"{base_sha}^{{commit}}"], required=True)
    run_git(["rev-parse", "--verify", f"{head_sha}^{{commit}}"], required=True)

    stat_out = run_git(["diff", "--stat", f"{base_sha}..{head_sha}"])
    log_out = run_git(["log", "--oneline", f"{base_sha}..{head_sha}"])
    diff_out = run_git(["diff", f"{base_sha}..{head_sha}"])

    pkg = [
        f"# Review Package: {base_sha[:8]}..{head_sha[:8]}",
        f"- **Base:** `{base_sha}`",
        f"- **Head:** `{head_sha}`",
        "",
        "## Commits",
        "```text",
        log_out or "(no commits)",
        "```",
        "",
        "## Diff Stat",
        "```text",
        stat_out or "(no changes)",
        "```",
        "",
        "## Full Diff",
        "```diff",
        diff_out or "(empty diff)",
        "```",
        "",
    ]

    content = "\n".join(pkg)
    if not out_path:
        out_path = root / ".superpowers" / "sdd" / "reviews" / f"diff-{base_sha[:8]}-{head_sha[:8]}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    common_p = argparse.ArgumentParser(add_help=False)
    common_p.add_argument(
        "-C",
        "--repo-dir",
        default=argparse.SUPPRESS,
        help="Run against a specific repository or git worktree directory instead of current directory",
    )

    parser = argparse.ArgumentParser(
        description="Cross-platform helper CLI for Subagent-Driven Development (SDD) & plan execution.",
        parents=[common_p],
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # workspace
    ws_p = subparsers.add_parser("workspace", parents=[common_p], help="Resolve or create plan workspace directory")
    ws_p.add_argument("plan_file", help="Path to implementation plan markdown file")

    # brief
    brief_p = subparsers.add_parser("brief", parents=[common_p], help="Extract one task's brief from plan file")
    brief_p.add_argument("plan_file", help="Path to implementation plan markdown file")
    brief_p.add_argument("task_id", help="Task ID or number (e.g. 1, 2, 2.1)")
    brief_p.add_argument("--out", "-o", default=None, help="Optional output brief path")

    # task-start (combines brief and HEAD SHA)
    start_p = subparsers.add_parser("task-start", parents=[common_p], help="Extract brief and print starting base commit SHA")
    start_p.add_argument("plan_file", help="Path to implementation plan markdown file")
    start_p.add_argument("task_id", help="Task ID or number")

    # review-package
    rev_p = subparsers.add_parser("review-package", parents=[common_p], help="Generate review diff package between two commits")
    rev_p.add_argument("base_sha", help="Base commit SHA or branch")
    rev_p.add_argument("head_sha", default="HEAD", nargs="?", help="Head commit SHA (default: HEAD)")
    rev_p.add_argument("--out", "-o", default=None, help="Optional output review package path")

    args = parser.parse_args()
    raw_repo_dir = getattr(args, "repo_dir", None)
    repo_override = Path(raw_repo_dir).resolve() if raw_repo_dir else None

    try:
        if args.subcommand == "workspace":
            plan = Path(args.plan_file).resolve()
            ws = get_sdd_workspace(plan, repo_root=repo_override)
            print(str(ws))
            return 0

        elif args.subcommand == "brief":
            plan = Path(args.plan_file).resolve()
            out_p = Path(args.out).resolve() if args.out else None
            brief_file = extract_task_brief(plan, args.task_id, out_p, repo_root=repo_override)
            line_count = len(brief_file.read_text(encoding="utf-8").splitlines())
            print(f"wrote {brief_file}: {line_count} lines")
            return 0

        elif args.subcommand == "task-start":
            plan = Path(args.plan_file).resolve()
            root = get_repo_root(repo_override or plan.parent)
            proc = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                raise RuntimeError(
                    f"Repository '{root}' has no commits yet. Create an initial commit before running task-start."
                )
            brief_file = extract_task_brief(plan, args.task_id, repo_root=root)
            print(f"brief: {brief_file}")
            print(f"base:  {proc.stdout.strip()}")
            return 0

        elif args.subcommand == "review-package":
            out_p = Path(args.out).resolve() if args.out else None
            pkg_file = build_review_package(args.base_sha, args.head_sha, out_p, repo_root=repo_override)
            print(f"wrote {pkg_file}")
            return 0

    except Exception as exc:
        print(f"[Error] {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
