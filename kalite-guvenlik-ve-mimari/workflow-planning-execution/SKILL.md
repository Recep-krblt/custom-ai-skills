---
name: workflow-planning-execution
description: Use before creating features, writing implementation plans, breaking down specs, executing multi-step tasks inline or via subagents, or dispatching parallel independent agents.
---

# Workflow: Brainstorming, Planning & Parallel Execution

Select the workflow matching your phase and read only the targeted reference file:

| Phase / Trigger | Reference Guide | Notes |
| :--- | :--- | :--- |
| Ambiguous requirements, design tradeoffs, MVP scoping | [references/brainstorming.md](references/brainstorming.md) | Clarify before editing; optional [builder check](references/builder-check-prompt.md) |
| Approved design -> exact file/TDD task plan | [references/writing-plans-and-breakdown.md](references/writing-plans-and-breakdown.md) | Includes vertical slicing & task sizing rules |
| Execute plan step-by-step (Inline or Subagent mode) | [references/executing-plans-modes.md](references/executing-plans-modes.md) | Ledger helper: [scripts/sdd_helper.py](scripts/sdd_helper.py) |
| 2+ unrelated tasks, test suites, or investigations | [references/parallel-agents.md](references/parallel-agents.md) | Concurrent `invoke_subagent` / `swarm` isolation |

> **Cross-Skill Contract:** Locate exact symbol ranges (`Lxx`) via `token-and-context-ops` (`.repo-map.md`, `--find`, `--callers`) before planning or dispatching parallel subagents, and sync `.repo-map.md` once verification completes.
