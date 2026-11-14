# Dispatching Parallel Agents

When multiple unrelated problems or workstreams exist, running them sequentially wastes wall-clock time and pollutes a single context window. Dispatch focused Antigravity subagents concurrently.

## When to Parallelize vs Keep Sequential

**Use parallel dispatch when ALL hold:**
- **2+ independent domains/files:** e.g., failing backend auth tests + failing frontend build + unrelated CLI script bug; or investigating 3 distinct modules.
- **No shared write targets:** Subagents using `Workspace: "inherit"` must NEVER edit the same files concurrently (if concurrent edits across shared files are needed, use `Workspace: "share"`/`"branch"` or `swarm` with `workspace: "share"`).
- **Clear verification per slice:** Each task has an objective check command or clear research deliverable.

**Do NOT parallelize when:**
- Failures share a single root cause (fixing A likely fixes B/C — diagnose A first via `quality-testing-review` (`references/systematic-debugging.md`)).
- Exploratory changes require reading global state to decide what to edit next.
- The whole job takes 1–2 quick tool calls in your own context.

## Dispatch Pattern in Antigravity

### Pattern A: Parallel Independent Tasks (`invoke_subagent`)
Call `invoke_subagent` multiple times in a **single turn**:
- `TypeName`: `"research"` for read-only codebase exploration/audit; `"self"` for isolated write+verify tasks; or `"browser"` for isolated web UI checks.
- `Workspace`: `"inherit"` for read-only tasks or strictly disjoint file paths; `"share"` or `"branch"` if workers build/edit/test concurrently in the repo.
- `Model`: `"inherit"` by default (`"flash"` for `browser` unless requested otherwise).

### Pattern B: Coordinated Multi-Worker Board (`swarm`)
For large projects needing ongoing coordination across writers, reviewers, and verifiers, use `swarm` (`action: "add"`, `workspace: "share"` for authors, default `"inherit"` for readers/verifiers).

## Writing Self-Contained Subagent Prompts

A subagent starts fresh and sees **nothing** from your conversation. Every prompt MUST contain:
1. **Exact Scope:** Exact files/directories/tests it owns (and explicit *"Do NOT edit files outside X"* boundary).
2. **Concrete Goal:** Question to answer or failing test/feature to fix.
3. **Constraints:** Relevent `GEMINI.md` / PowerShell conventions, existing helpers to reuse.
4. **Expected Output:** Return modified files, exact verification commands run, and raw pass/fail counts (or `file#Lstart-Lend` citations for research).

## Integration Gate After Subagents Finish

Do not blindly summarize subagent claims (`quality-testing-review` (`references/verification-before-completion.md`)):
1. If any subagent used `"share"`/`"branch"`, review and integrate its diff cleanly.
2. Check for cross-file interface/type mismatches across parallel workers.
3. **Run the combined test/build suite yourself** via `run_command` after merging all changes and observe passing output before reporting completion.
