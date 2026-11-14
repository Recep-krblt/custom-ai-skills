# Systematic Debugging

Random fixes waste tokens and mask underlying faults. Find the root cause before writing a single fix.

**Iron Law:**
```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```
If you have not completed Phase 1, you may not propose fixes. Symptom patches ("just add a null check", "retry once", "increase timeout") are prohibited.

## When to Use

Trigger on **any** technical issue: test failures, production bugs, unexpected API/UI behavior, build failures, flaky/race tests, or integration errors — **especially** under time pressure, when a quick fix seems obvious, or after previous fixes failed.

## The Four Phases

Complete each phase before moving to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting any fix:**
1. **Read error messages completely:** Do not skim stack traces. Note exact exit codes, line numbers, file paths, and failing assertions.
2. **Reproduce consistently:** Trigger the failure reliably with the exact command or payload. If non-deterministic, inspect timing/state dependencies instead of guessing.
3. **Locate with Map-First:** Check `.repo-map.md` (or run `token-and-context-ops` (`references/repo-map-guide.md`) `--find`) and recent `git diff` / `git log -n 10` to see what changed near the failure.
4. **Gather diagnostic evidence across boundaries:** For multi-component flows (UI → API → DB → External/OS, CI → build → runtime), temporarily log what data enters and leaves each boundary once to pinpoint which layer breaks before forming a hypothesis.
5. **Trace data flow backward:** Never fix where the error finally crashes — trace bad values backward up the call stack to where they originated.
   - Deep technique: [root-cause-tracing.md](root-cause-tracing.md)
   - For memory leaks, heap snapshots, and >50ms event-loop stalls: [profiling-and-heap-analysis.md](profiling-and-heap-analysis.md)
   - For test pollution (an unwanted file/state created during test runs): run `python ../scripts/find_polluter.py <artifact-glob> "<test-glob>"` (see [../scripts/find_polluter.py](../scripts/find_polluter.py)).

### Phase 2: Pattern Analysis

1. **Find working examples:** Locate similar working code in the same repository (via `.repo-map.md` or `rg`) and compare line-by-line against the broken path.
2. **Check assumptions against real code/docs:** Verify actual library/runtime APIs, types, encoding (Windows `cp1254` vs `utf-8`, CRLF vs LF, path separators), environment variables, and schemas.
3. **List every difference:** Assume every difference between the working path and broken path matters until ruled out.

### Phase 3: Hypothesis and Minimal Testing

1. **State one explicit hypothesis:** `"I hypothesize X causes Y because evidence Z shows..."`
2. **Test minimally:** Change **one variable at a time** — do not bundle multiple speculative edits together.
3. **Evaluate:** If it works cleanly, proceed to Phase 4. If it fails, **revert it** and form a new hypothesis based on what you observed — never stack unverified fixes.

### Phase 4: Implementation and Verification

1. **Create a failing test first (TDD):** Follow `quality-testing-review` (`references/tdd-and-testing-patterns.md`) to write the simplest automated reproduction test that fails on the current bug before applying the fix.
2. **Implement a single root-cause fix:** Fix the origin identified in Phase 1, then apply **defense-in-depth** validation across callers/boundaries where appropriate:
   - Guide: [defense-in-depth.md](defense-in-depth.md)
   - For flaky async tests/arbitrary sleeps: replace `sleep`/`setTimeout` polling with [condition-based-waiting.md](condition-based-waiting.md) and [condition-based-waiting-example.ts](condition-based-waiting-example.ts).
3. **Verify end-to-end (`quality-testing-review` (`references/verification-before-completion.md`)):** Re-run the failing test AND the broader affected suite via `run_command` after your final edit and observe 0 failures.

## Circuit Breaker: The 3-Fix Rule

**If 3 or more consecutive fixes fail:**
- **STOP editing code.** This signals an **architectural assumption is wrong**, not just a typo or edge case.
- Step back and question whether the state model, coupling, or abstraction itself is flawed.
- Explain the mismatch and evidence directly to the user before attempting Fix #4.

## Antigravity Execution Notes

- Read failing logs economically with PowerShell filtering (`Select-String`, `-Tail 80`) per token efficiency rules.
- For complex multi-subsystem failures (e.g., 3+ failing test suites with distinct errors), dispatch parallel `research` subagents or use `workflow-planning-execution` (`references/parallel-agents.md`) after isolating independent failure domains.
- Never claim a bug is "fixed" without running the exact failing command after the last edit (`quality-testing-review` (`references/verification-before-completion.md`)).
