# Repository Structure Audit & Safe Reorganization Guide

Methodology for inspecting project directory layouts, identifying clutter/orphans/structural drift, and reorganizing files without breaking imports, embeds, CI pipelines, or git history (inspired in part by MIT `peetwan/repo-cleanup-skill` report-before-move discipline).

## Core Rule: Report Before Moving or Deleting

Never move, rename, or delete tracked files or directories in the first pass. Always run a read-only audit first, check inbound references across source AND non-code config files, and present a structured proposal with risk levels before executing moves.

---

## Phase 1: Read-Only Layout & Clutter Audit

Run the bundled scanner alongside `.repo-map.md` (`--stats`) when available:
```powershell
python "<SKILLS_DIR>/workflow-planning-execution/scripts/audit_repo_layout.py" <repo-root>
```
Review five structural signals:
1. **Root Clutter:** Local DBs (`*.db`, `*.sqlite`), exported JSON/CSV dumps, stray images/HTML mockups, or logs sitting at the repo root instead of `.gitignore`d scratch dirs or dedicated data/assets folders.
2. **Stale / Cruft & Ignored Gaps:** `*.bak`, `*.orig`, `*.tmp`, `*.old`, `*.log`, OS cruft (`.DS_Store`, `Thumbs.db`), empty directories, and runtime artifacts accidentally tracked by `git ls-files`.
3. **Excessive Depth or Flat Pileups:** Directories nested `>5` levels deep or a flat folder dumping 30+ unrelated modules together.
4. **Architectural Layout Fit:**
   - Group growing modules by **domain/feature** (`internal/<domain>/`, `src/features/<domain>/`) rather than splitting small single-use files into global type-soup (`utils/`, `types/`, `constants/`).
   - **Go:** `cmd/<app>/main.go`, cohesive `internal/<pkg>/` slices, `migrations/`, `scripts/`.
   - **Python:** `src/<pkg>/`, `tests/`, `scripts/` alongside root `pyproject.toml`.
   - **Web / TS:** `src/app/` or `src/features/<domain>/` with shared primitives under `src/components/` or `src/lib/`.
5. **Orphan & Dead-Asset Candidates:** Check inbound references across the *entire* repo before flagging any file as unused.

---

## Phase 2: Inbound Reference & Blast-Radius Check

Code `import` searches alone miss non-code path dependencies. Before recommending deletion or a move for `<target>`, scan:
- **Symbol & Code Callers:** `.repo-map.md --callers` (`token-and-context-ops`) or `git grep -n -F "<filename>" -- . ":(exclude)<target>"`.
- **Non-Code Path Consumers:** Explicitly check `Dockerfile`, `docker-compose*.yml`, `.github/workflows/*.yml`, `Makefile`, `package.json` scripts, `pyproject.toml`, `go:embed` directives, HTML/CSS `src`/`href`, and `.gitignore`.
- Classify every proposed action clearly:
  - **Low Risk (Approve/Batch):** Untracked OS cruft, empty dirs, temp/log leftovers, orphaned stale previews with 0 references.
  - **Medium Risk (Explicit Review):** Moving active modules (`git mv`), updating `go:embed` / build config paths, removing obsolete docs/ADRs.
  - **High Risk (Preserve Unless Explicit):** Migrations, DB schemas, security configs, license/notice files, `.env*` templates.

---

## Phase 3: Zero-Breakage Execution Protocol (Post-Approval)

1. **Preserve History with `git mv`:** Move/rename git-tracked files strictly via `git mv <old> <new>` rather than copy+delete so `git log --follow` history stays intact.
2. **Update All Consumers Atomically:** Update language imports, package declarations (e.g., Go import paths), CI/Docker paths, relative doc links, and test fixtures in the same change set.
3. **Clean Empty Parents & Check Ignored Leaks:** Remove orphaned empty directories and update `.gitignore` if runtime logs/DBs were accumulating in root.
4. **Verify End-to-End Before Reporting (`verification-before-completion.md`):**
   - Run full build, linter, and test suite (`go test ./...`, `pytest`, `npm test` / `tsc --noEmit`).
   - Check `git status` and broken markdown/config links.
   - If `.repo-map.md` exists, run `generate_repo_map.py` once after all moves succeed so line numbers and file sections reflect the new layout.
