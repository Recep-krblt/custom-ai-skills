#!/usr/bin/env python3
"""Deterministic validator for Antigravity skill and local plugin directories.

Checks:
- Required YAML frontmatter (`name`, `description`)
- Folder name == `name`, valid kebab-case slug, <= 64 chars
- `description` non-empty, <= 1024 chars (warns if > 500 chars)
- Relative markdown links inside all `.md` files resolve on disk (outside fenced code blocks)
- `license: Complete terms in LICENSE.txt` matches an existing `LICENSE.txt`
- All `.py` scripts compile cleanly with `py_compile`
- Optional `--plugin <dir>`: validates `plugin.json` strict schema + bundled `skills/*`
- Optional `--check-plugins-root <dir>`: verifies global unique skill names across all plugins
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
SKIP_URL_PREFIXES = ("http://", "https://", "mailto:", "file://", "#", "conversation://", "customization://")
ALLOWED_PLUGIN_KEYS = {
    "name",
    "description",
    "logo",
    "suggestedPrompts",
    "displayName",
    "version",
    "author",
    "homepage",
    "repository",
    "disabled",
}


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str, str | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "Missing opening YAML frontmatter delimiter '---'"

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, text, "Missing closing YAML frontmatter delimiter '---'"

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])
    data: dict[str, str] = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, raw_val = line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()

        if val in {"|", "|-", ">", ">-"}:
            block: list[str] = []
            i += 1
            while i < len(fm_lines) and (fm_lines[i].startswith(" ") or fm_lines[i].startswith("\t") or not fm_lines[i].strip()):
                block.append(fm_lines[i].strip())
                i += 1
            joiner = "\n" if val.startswith("|") else " "
            data[key] = joiner.join(part for part in block if part).strip()
            continue

        if (val.startswith('"') and val.endswith('"') and len(val) >= 2) or (
            val.startswith("'") and val.endswith("'") and len(val) >= 2
        ):
            val = val[1:-1]
            i += 1
        else:
            parts = [val] if val else []
            i += 1
            while i < len(fm_lines) and (fm_lines[i].startswith("  ") or fm_lines[i].startswith("\t")):
                parts.append(fm_lines[i].strip())
                i += 1
            val = " ".join(parts).strip()

        data[key] = val

    return data, body, None


def extract_markdown_links_outside_fences(text: str) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    in_fence = False
    fence_char = ""
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_char = marker
            elif marker == fence_char:
                in_fence = False
            continue
        if in_fence:
            continue
        cleaned = re.sub(r"`[^`]*`", "", line)
        for match in MD_LINK_RE.finditer(cleaned):
            links.append((line_no, match.group(1).strip()))
    return links


def validate_skill(skill_dir: Path) -> tuple[list[str], list[str], str | None]:
    errors: list[str] = []
    warnings: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append("Missing SKILL.md")
        return errors, warnings, None

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, _, fm_err = parse_frontmatter(text)
    if fm_err or fm is None:
        errors.append(fm_err or "Invalid frontmatter")
        return errors, warnings, None

    name = fm.get("name", "").strip()
    desc = fm.get("description", "").strip()

    if not name:
        errors.append("Frontmatter missing 'name'")
    else:
        if name != skill_dir.name:
            errors.append(f"Frontmatter name '{name}' does not match folder '{skill_dir.name}'")
        if len(name) > 64 or not NAME_RE.match(name):
            errors.append(f"Invalid skill name '{name}' (must be kebab-case <= 64 chars)")

    if not desc:
        errors.append("Frontmatter missing 'description'")
    else:
        if len(desc) > 1024:
            errors.append(f"Description exceeds 1024 chars ({len(desc)} chars)")
        elif len(desc) > 500:
            warnings.append(f"Description is {len(desc)} chars (>500; trim for lean prompt injection)")

    lic_field = fm.get("license", "")
    if "LICENSE.txt" in lic_field and not (skill_dir / "LICENSE.txt").is_file():
        errors.append("Frontmatter cites LICENSE.txt but LICENSE.txt is missing")

    for md_file in sorted(skill_dir.rglob("*.md")):
        if any(part in SKIP_DIRS for part in md_file.parts):
            continue
        md_text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_no, target in extract_markdown_links_outside_fences(md_text):
            if not target or target.startswith(SKIP_URL_PREFIXES):
                continue
            target_no_anchor = target.split("#", 1)[0].split("?", 1)[0].strip()
            if not target_no_anchor or target_no_anchor.startswith("<"):
                continue
            resolved = (md_file.parent / target_no_anchor).resolve()
            if not resolved.exists():
                rel_md = md_file.relative_to(skill_dir)
                errors.append(f"Broken link in {rel_md}:{line_no} -> {target}")

    for py_file in sorted(skill_dir.rglob("*.py")):
        if any(part in SKIP_DIRS for part in py_file.parts):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            rel_py = py_file.relative_to(skill_dir)
            errors.append(f"Python syntax error in {rel_py}: {exc.msg}")

    return errors, warnings, (name or None)


def validate_plugin_dir(plugin_dir: Path) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_names: list[str] = []

    manifest = plugin_dir / "plugin.json"
    if not manifest.is_file():
        return [f"Missing plugin.json in {plugin_dir}"], warnings, skill_names

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON in plugin.json: {exc}"], warnings, skill_names

    unknown = set(data.keys()) - ALLOWED_PLUGIN_KEYS
    if unknown:
        errors.append(f"Unknown top-level plugin.json key(s): {sorted(unknown)}")
    pname = str(data.get("name", "")).strip()
    pdesc = str(data.get("description", "")).strip()
    if not pname or not NAME_RE.match(pname):
        errors.append(f"Invalid or missing plugin 'name': {pname!r}")
    if not pdesc:
        errors.append("Missing plugin 'description'")

    skills_sub = plugin_dir / "skills"
    if skills_sub.is_dir():
        for sd in sorted(p for p in skills_sub.iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
            serr, swarn, sname = validate_skill(sd)
            errors.extend(f"[{sd.name}] {e}" for e in serr)
            warnings.extend(f"[{sd.name}] {w}" for w in swarn)
            if sname:
                skill_names.append(sname)

    return errors, warnings, skill_names


def validate_skills_root(root: Path) -> tuple[int, int, list[str]]:
    skill_dirs = sorted(
        p for p in root.iterdir()
        if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")
    )
    if not skill_dirs:
        print(f"[Error] No skill subdirectories found in {root}", file=sys.stderr)
        return 1, 0, []

    total_errors = 0
    total_warnings = 0
    found_names: list[str] = []
    for sdir in skill_dirs:
        errors, warnings, sname = validate_skill(sdir)
        if sname:
            found_names.append(sname)
        total_errors += len(errors)
        total_warnings += len(warnings)
        if errors:
            print(f"[FAIL] {sdir.name}")
            for err in errors:
                print(f"       ERROR: {err}")
            for warn in warnings:
                print(f"       WARN : {warn}")
        elif warnings:
            print(f"[WARN] {sdir.name}")
            for warn in warnings:
                print(f"       WARN : {warn}")
        else:
            print(f"[PASS] {sdir.name}")

    print(f"\nSummary: {len(skill_dirs)} skills checked, {total_errors} error(s), {total_warnings} warning(s).")
    return total_errors, total_warnings, found_names


def main() -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Validate Antigravity skills and local plugins.")
    parser.add_argument(
        "skills_root",
        nargs="?",
        default=str(Path.home() / ".gemini" / "config" / "skills"),
        help="Path to skills root directory (default: ~/.gemini/config/skills)",
    )
    parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Path to a local plugin directory to validate (repeatable).",
    )
    parser.add_argument(
        "--check-plugins-root",
        default=None,
        help="Check global skill name uniqueness across all plugins in this directory.",
    )
    args = parser.parse_args()

    total_errors = 0
    seen_names: dict[str, str] = {}

    if not args.plugin or Path(args.skills_root).resolve().exists():
        root = Path(args.skills_root).resolve()
        if not root.is_dir():
            print(f"[Error] Skills root not found: {root}", file=sys.stderr)
            return 2
        errs, _, names = validate_skills_root(root)
        total_errors += errs
        for n in names:
            seen_names[n] = str(root / n)

    for p_str in args.plugin:
        pdir = Path(p_str).resolve()
        if not pdir.is_dir():
            print(f"[Error] Plugin directory not found: {pdir}", file=sys.stderr)
            return 2
        errs, warns, pnames = validate_plugin_dir(pdir)
        total_errors += len(errs)
        for n in pnames:
            if n in seen_names:
                errs.append(f"Duplicate skill name '{n}' collides with {seen_names[n]}")
                total_errors += 1
            else:
                seen_names[n] = str(pdir / "skills" / n)
        status = "FAIL" if errs else ("WARN" if warns else "PASS")
        print(f"[{status}] plugin:{pdir.name} ({len(pnames)} skill(s))")
        for e in errs:
            print(f"       ERROR: {e}")
        for w in warns:
            print(f"       WARN : {w}")

    if args.check_plugins_root:
        proot = Path(args.check_plugins_root).resolve()
        if proot.is_dir():
            for pdir in sorted(d for d in proot.iterdir() if d.is_dir()):
                sdir = pdir / "skills"
                if not sdir.is_dir():
                    continue
                for sd in sorted(x for x in sdir.iterdir() if x.is_dir()):
                    loc = str(sd)
                    if sd.name in seen_names and Path(seen_names[sd.name]).resolve() != sd.resolve():
                        print(f"[FAIL] Duplicate skill '{sd.name}': {seen_names[sd.name]} <-> {loc}")
                        total_errors += 1
                    seen_names.setdefault(sd.name, loc)
            print(f"Global uniqueness check across plugins completed ({len(seen_names)} unique skills).")

    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
