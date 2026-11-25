---
name: workflow-planning-execution
description: Use before creating features, writing implementation plans, designing deep modules/seams, auditing or reorganizing project directory layouts, executing multi-step tasks, or dispatching parallel agents.
---

# Workflow: Brainstorming, Planning & Parallel Execution

Select the workflow matching your phase and read only the targeted reference file:

| Phase / Trigger | Reference Guide | Notes |
| :--- | :--- | :--- |
| Ambiguous requirements, design tradeoffs, MVP scoping | [references/brainstorming.md](references/brainstorming.md) | Clarify before editing; optional [builder check](references/builder-check-prompt.md) |
| Deep module boundaries, seams & architecture audit | [references/architecture-design.md](references/architecture-design.md) | Deep vs. shallow modules, Deletion Test, dependency injection |
| Directory layout audit, clutter/orphan scan & safe `git mv` reorganization | [references/repo-structure-and-cleanup.md](references/repo-structure-and-cleanup.md) | Scanner: [scripts/audit_repo_layout.py](scripts/audit_repo_layout.py) |
| Approved design -> exact file/TDD task plan | [references/writing-plans-and-breakdown.md](references/writing-plans-and-breakdown.md) | Includes vertical slicing & task sizing rules |
| Execute plan step-by-step (Inline or Subagent mode) | [references/executing-plans-modes.md](references/executing-plans-modes.md) | Ledger helper: [scripts/sdd_helper.py](scripts/sdd_helper.py) |
| 2+ unrelated tasks, test suites, or investigations | [references/parallel-agents.md](references/parallel-agents.md) | Concurrent `invoke_subagent` / `swarm` isolation |

> **Cross-Skill Contract:** Locate exact symbol ranges (`Lxx`) via `token-and-context-ops` (`.repo-map.md`, `--find`, `--callers`) before planning or dispatching parallel subagents, and sync `.repo-map.md` once verification completes.
