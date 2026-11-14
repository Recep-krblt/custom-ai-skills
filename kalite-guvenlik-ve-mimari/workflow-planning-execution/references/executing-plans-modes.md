# Executing Plans (Inline & Subagent Modes)

Execute an implementation plan cleanly without drift, context rot, or skipped verification. Choose the execution mode that matches task size and coupling.

## Selecting Execution Mode

| Condition | Mode | Why |
| --- | --- | --- |
| 1–3 small or tightly coupled tasks; low context growth | **Inline Mode** | Single context, minimal dispatch overhead |
| 4+ independent tasks, or high risk of context rot (>80K tokens) | **Subagent Mode** | Fresh implementer + independent reviewer per task keeps coordinator context clean |

## Shared Rules (Both Modes)

- **Workspace & Ledger:** Initialize `<repo-root>/.superpowers/sdd/<plan-slug>/` and inspect `progress.md` before starting:
  ```powershell
  python "C:\Users\<USERNAME>\.gemini\config\skills\workflow-planning-execution\scripts\sdd_helper.py" workspace <plan_file>
  ```
  If resuming after compaction or restart, read [resuming.md](resuming.md) — completed tasks in `progress.md` / `git log` are never re-implemented.
- **Continuous Execution & Rulings:** Do not pause between tasks to ask *"should I continue?"*. Record minor plan adjustments in `progress.md` as `Ruling: <decision> — <why> — <cost if wrong>`. Stop **only** for destructive/irreversible actions, security-sensitive credentials, external publishes, or broken plans where forward steps are pure guesswork.
- **TDD & Anti-Hang Gate:** Every behavior step requires watched `RED` → minimal `GREEN` (`quality-testing-review` (`references/tdd-and-testing-patterns.md`), using `run_with_timeout.py` / non-interactive flags).

---

## Mode A: Subagent-Driven Execution (`4+ tasks`)

1. **Preflight:** Run the conflict scan in [preflight.md](preflight.md) before Task 1.
2. **Extract Brief:** Keep coordinator context tiny by extracting one task into `<workspace>/task-<N>-brief.md`:
   ```powershell
   python "C:\Users\<USERNAME>\.gemini\config\skills\workflow-planning-execution\scripts\sdd_helper.py" brief <plan_file> <task_id>
   ```
3. **Dispatch Implementer:** Use `invoke_subagent` (`TypeName: "self"`, `Role: "Task Implementer"`) with [implementer-prompt.md](implementer-prompt.md). Review report claims objectively ([handling-reports.md](handling-reports.md)); small independent batches follow [batching.md](batching.md).
4. **Dispatch Task Reviewer:** Generate diff package and dispatch fresh reviewer using [task-reviewer-prompt.md](task-reviewer-prompt.md):
   ```powershell
   python "C:\Users\<USERNAME>\.gemini\config\skills\workflow-planning-execution\scripts\sdd_helper.py" review-package <base_sha> HEAD
   ```
   If issues arise, run scoped fix passes per [fix-loop.md](fix-loop.md) and [re-review-prompt.md](re-review-prompt.md).
5. **Ledger Update:** Append `- Task <id>: complete (Commit: <sha>)` to `progress.md` and proceed immediately.
6. **Whole-Branch Final Review:** Finish per [final-review.md](final-review.md) and [code-reviewer.md](code-reviewer.md).

---

## Mode B: Inline Execution (`1–3 tasks`)

1. **Task Start:** Extract brief and record base SHA in one call:
   ```powershell
   python "C:\Users\<USERNAME>\.gemini\config\skills\workflow-planning-execution\scripts\sdd_helper.py" task-start <plan_file> <task_id>
   ```
2. **Implement with TDD:** Execute steps strictly per brief (`RED` → `GREEN`), using `quality-testing-review` (`references/systematic-debugging.md`) if output diverges and [cannot-verify.md](cannot-verify.md) if a check is blocked externally.
3. **Commit & Ledger:** Commit conventionally (`devops-git-cicd` (`references/git-workflows-and-recovery.md`)) and record `- Task <id>: complete (Commit: <sha>)` in `progress.md`.
4. **Final Review:** Inspect the full branch diff (`quality-testing-review` (`references/code-review-and-checklist.md`)).

---

## Final Completion Gate (`quality-testing-review` (`references/verification-before-completion.md`))

Before reporting completion or cleaning up `<workspace>/`, re-run the full build and test suite via `run_command` after your final edit and verify 0 errors (`quality-testing-review` (`references/verification-before-completion.md`) + `devops-git-cicd` (`references/git-workflows-and-recovery.md`)).
