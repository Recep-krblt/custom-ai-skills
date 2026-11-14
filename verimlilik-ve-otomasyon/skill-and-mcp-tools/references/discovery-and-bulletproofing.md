# Skill Discovery Optimization (SDO) & Bulletproofing Reference

## 1. Writing Trigger-Only Descriptions

When an agent sees a `description` containing a workflow summary, it often executes from that summary instead of calling `read_file` on `SKILL.md`.

| Bad (Workflow Spoiler) | Good (Trigger Conditions Only) |
| --- | --- |
| `Creates plans by reading repo map, breaking into 5 steps, adding TDD tests, and running self-review.` | `Use when you have an approved design or multi-file task and need a concrete step-by-step implementation plan before coding.` |
| `Investigates bugs in 4 phases: trace root cause, compare patterns, form 1 hypothesis, write failing test first.` | `Use when encountering any bug, test failure, flaky timing behavior, or unexpected runtime error before proposing fixes.` |
| `Runs pytest or vitest, mocks DB, checks 80% coverage, and validates edge cases.` | `Use when implementing features with TDD, writing unit/integration tests, isolating mocks, or building edge-case test suites.` |

### Description Checklist
- Starts with `"Use when..."` (or direct trigger conditions + negative boundaries like `"Do not use for..."` when disambiguation is needed).
- Third-person / action-trigger phrasing; never includes hidden implementation checklists.
- Under 500 characters whenever possible (hard limit: 1024).

## 2. Bulletproofing Discipline Skills Against Rationalization

Agents under time pressure or perceived "trivial change" bias skip rules unless loopholes are explicitly sealed.

- **State Iron Laws concisely** when a rule is non-negotiable (e.g., `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`).
- **Add an Anti-Rationalization table** mapping common excuses (`"It's just a one-line fix"`, `"I'm confident it works"`) to why the excuse fails and what the rule requires instead.
- **Avoid redundant verbosity:** A crisp 3-row table beats a 4-paragraph lecture.

## 3. Antigravity Tool Mapping When Porting External Skills

When adapting skills from external repos (e.g., Claude Code / Codex / Cursor skills), translate host assumptions:

| External Term | Antigravity Equivalent |
| --- | --- |
| `bash` tool / Unix `/tmp/` | `run_command` (Windows PowerShell) / `tempfile.gettempdir()` or `$env:TEMP` |
| `Task` / `Agent` subagent dispatch | `invoke_subagent` (`TypeName`: `research` / `self` / `browser`) or `swarm` |
| `TodoWrite` | Task markdown artifact (`<appDataDir>\brain\<id>\task.md`) — NOT `manage_task` |
| `CLAUDE.md` | `GEMINI.md` / `<user_rules>` |
| `Read` / `Edit` / `Write` | `read_file` / `edit_file` / `write_file` |
| `AskUserQuestion` | `ask_question` (bounded multi-choice) or direct text question (open-ended) |

## 4. Testing Skills with `invoke_subagent`

For critical skills:
1. Run `invoke_subagent` (`TypeName: "research"` or `"self"`) on a realistic pressure prompt referencing the target skill path.
2. Verify it cites the exact gates, picks the right script/reference, and avoids the documented rationalizations.
3. Refine `SKILL.md` only where real observed failures occurred; re-run validation afterwards.
