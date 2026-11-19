# Codebase Skeleton & Repository Map (repo-map)

This skill provides deterministic, token-efficient codebase navigation for multi-module architectures, web portals, and large codebases (e.g., <PROJECT_NAME>, enterprise apps). It stops agents from burning context windows on blind file exploration (`read_file`, wide `grep`).

## Activation Criteria
- **Trigger When:** 
  - Working on multi-file repositories or unfamiliar codebases.
  - User asks to "scan project", "analyze architecture", "find where X is defined", or troubleshoot across modules.
  - Prior to reading multiple files or locating symbols (controllers, models, routes, templates, components).
- **Do NOT Trigger When:** Working on isolated single-file scripts or when the exact file path and line number are already explicitly provided.

---

## Standard Protocol: "Map-First" Navigation

The agent MUST follow this 5-tier navigation & sync sequence without deviation:

### Tier 1: Check or Synchronize the Map
Check if `.repo-map.md` exists in the project root. If missing or stale (files modified/added), execute the generator script:
```powershell
python "$HOME/.gemini/config/skills/token-and-context-ops/scripts/generate_repo_map.py" .
```
For instant symbol lookup (supports `|` OR queries) without parsing the entire markdown file:
```powershell
python "$HOME/.gemini/config/skills/token-and-context-ops/scripts/generate_repo_map.py" . --find "SymbolA|SymbolB|POST /admin"
```

### Tier 2: Zero Blind Reads
NEVER read whole files or run wide directory searches to guess where functions, classes, or HTML elements live. Always inspect `.repo-map.md` first to identify exact file paths and symbol line ranges (`Lxx` or `Lxx-Lyy`).

### Tier 3: Surgical Inspection
Once the target symbol is identified in the map, use `read_file` with exact `StartLine` and `EndLine` parameters matching the `(Lxx-Lyy)` range to pull only the relevant block into context.

### Tier 4: Fallback & Non-Abandonment Guarantee
If the problem is a runtime bug, subtle logic flaw, CSS collision, or side-effect that cannot be pinpointed solely from method signatures in the map:
- **NEVER dismiss the issue** or conclude that "no problem exists".
- Escalate immediately to targeted token-filtered searches (`Select-String` / targeted regex on specific error keywords) or `quality-testing-review` (`references/systematic-debugging.md`).
- Read the suspect file in full or inspect runtime logs/tests until the root cause is resolved (`quality-testing-review` (`references/verification-before-completion.md`)).

### Tier 5: Task-End Sync Rule
- **When to Sync:** Whenever `.repo-map.md` already exists in the repository AND any indexed file (code, template, stylesheet, config, or docs) was edited, added, or removed during the task (since line ranges `Lxx-Lyy` shift even without new files).
- **Timing:** Run `python "$HOME/.gemini/config/skills/token-and-context-ops/scripts/generate_repo_map.py" .` **once** right after all edits and verification tests pass—never after intermediate edits (v4 incremental symbol caching in `.repo-map.cache.json` reparses only changed files).
- **Scope Guard:** Do not create `.repo-map.md` unprompted in small/single-file projects that do not already have one unless the user explicitly asks to scan/map the project.

> **CLI Options:** `--check` (exit 0 fresh / 2 stale; validates explicit `--compact`/`--no-wiring`/`--max-symbols` options too), `--compact` (omit individual test cases and CSS selector lists in markdown; `--find` still searches everything), `--no-wiring` (omit `## Cross-References & Wiring`), `--find "A|B|C"` (searches symbols, paths, and wiring refs; combine with `--in <subpath>` and `--regex`), `--changed` (symbols for git-changed files, falling back past map-only `HEAD` sync commits), `--stats` (LOC & token hotspot summary), `--install-hook` (add idempotent `post-commit`/`post-merge` hooks; note: `post-commit` updates `.repo-map.md` in the working tree leaving it unstaged), `--max-symbols 0` (lift per-file cap). Writing a scoped map via `--in` requires `--output <file>` so root `.repo-map.md` is not overwritten. Indexes `.github/workflows` alongside Go (incl. `{{define}}` templates & internal wiring), HTML (`#id` + inline JS), CSS (`@media`/`@keyframes`/vars), JS/TS (`window.*` exports), Python, Rust, SQL, YAML, JSON, Makefile, Dockerfile, PowerShell, and Markdown.
