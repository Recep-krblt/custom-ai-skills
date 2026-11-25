#!/usr/bin/env python3
"""Static-to-Dynamic Migration Auditor.

Scans frontend templates, HTML, CSS, JS/TS, and Go/Jinja template directories
for common hardcoded migration hazards (static .html links, relative asset paths,
hardcoded localhost URLs, inline object arrays in UI files, placeholder contacts,
and unsafe raw-HTML rendering sinks) with exact file#Lx citations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

TARGET_EXTS = {
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".astro",
    ".vue",
    ".svelte",
    ".tmpl",
    ".gohtml",
    ".tpl",
    ".jinja",
    ".jinja2",
}

UI_ARRAY_EXTS = {".js", ".jsx", ".ts", ".tsx", ".astro", ".vue", ".svelte"}

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".astro",
    "dist",
    "build",
    "out",
    "coverage",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".superpowers",
    ".site-builds",
}


@dataclass(slots=True)
class Finding:
    category: str
    severity: str
    file: str
    line: int
    snippet: str


RULES: list[tuple[str, str, re.Pattern[str], set[str] | None]] = [
    (
        "unsafe_raw_html_sink",
        "P0",
        re.compile(
            r"(dangerouslySetInnerHTML\s*=|\.innerHTML\s*=|template\.HTML\s*\(|\|\s*safe\b|set:html\s*=)"
        ),
        None,
    ),
    (
        "hardcoded_origin",
        "P1",
        re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?"),
        None,
    ),
    (
        "static_html_link",
        "P1",
        re.compile(
            r"""href\s*=\s*["'](?!https?:|mailto:|tel:|#)(?:[^"']*\.html?(?:[?#][^"']*)?)["']""",
            re.IGNORECASE,
        ),
        None,
    ),
    (
        "relative_or_static_asset_path",
        "P2",
        re.compile(
            r"""(?:(?:src|href|poster|data-src)\s*=\s*["']|url\(\s*["']?)(?!(?:https?:|data:|blob:|\{\{|\$\{))(?:\.?\.?/)?(?:assets|images|img|static|media|fonts)/[^"')\s>]+""",
            re.IGNORECASE,
        ),
        None,
    ),
    (
        "inline_static_data_array",
        "P2",
        re.compile(r"\b(?:const|let|var)\s+[A-Za-z_][A-Za-z0-9_]*\s*(?::[^=]+)?=\s*\[\s*\{"),
        UI_ARRAY_EXTS,
    ),
    (
        "hardcoded_contact_uri",
        "P3",
        re.compile(r"""href\s*=\s*["'](?:mailto:|tel:)[^"'{}]+["']""", re.IGNORECASE),
        None,
    ),
]


def iter_source_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() in TARGET_EXTS else []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TARGET_EXTS:
            files.append(path)
    return files


def scan_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for base in paths:
        rel_root = base.parent if base.is_file() else base
        for file_path in iter_source_files(base):
            ext = file_path.suffix.lower()
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(file_path.relative_to(rel_root)).replace("\\", "/")
            for lineno, line_text in enumerate(text.splitlines(), start=1):
                stripped = line_text.strip()
                if not stripped or stripped.startswith("//") or stripped.startswith("<!--"):
                    continue
                for cat, sev, pattern, exts in RULES:
                    if exts is not None and ext not in exts:
                        continue
                    if pattern.search(line_text):
                        snippet = stripped if len(stripped) <= 120 else stripped[:117] + "..."
                        findings.append(
                            Finding(
                                category=cat,
                                severity=sev,
                                file=rel,
                                line=lineno,
                                snippet=snippet,
                            )
                        )
    return findings


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Audit static websites/templates for hardcoded routes, assets, arrays, and raw-HTML XSS sinks."
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--limit", type=int, default=15, help="Max findings printed per category (default: 15)")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when P0/P1 findings are detected")
    args = parser.parse_args()

    targets = [Path(p).resolve() for p in args.paths]
    missing = [str(p) for p in targets if not p.exists()]
    if missing:
        print(f"[Error] Path(s) not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    findings = scan_paths(targets)
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        grouped[f.category].append(f)

    if args.format == "json":
        payload = {
            "total": len(findings),
            "counts": {k: len(v) for k, v in grouped.items()},
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Static-to-Dynamic Audit: {len(findings)} finding(s) across {len(grouped)} category(ies).")
        for cat in sorted(grouped):
            items = grouped[cat]
            sev = items[0].severity
            print(f"\n[{sev}] {cat} ({len(items)})")
            for item in items[: args.limit]:
                print(f"  - {item.file}#L{item.line}: {item.snippet}")
            if len(items) > args.limit:
                print(f"  ... ({len(items) - args.limit} more omitted; raise --limit to inspect)")

    if args.strict and any(f.severity in ("P0", "P1") for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
