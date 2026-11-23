---
name: quality-testing-review
description: Use when debugging bugs/flaky tests/leaks, writing TDD tests (with anti-hang timeouts), performing PR/code review, simplifying complex code, or verifying work before claiming completion.
---

# Quality: Debugging, TDD, Code Review & Verification

Select the required engineering gate before editing or reporting results:

| Need / Trigger | Reference Guide | Key Rule / Tool |
| :--- | :--- | :--- |
| Bugs, failing tests, leaks, event-loop stalls | [references/systematic-debugging.md](references/systematic-debugging.md) | Root cause first; 3-fix circuit breaker; [find_polluter.py](scripts/find_polluter.py) |
| Unit/integration tests, RED-GREEN-Refactor, mocks | [references/tdd-and-testing-patterns.md](references/tdd-and-testing-patterns.md) | Watch-RED-Fail; watchdog [run_with_timeout.py](scripts/run_with_timeout.py) |
| Pre-completion proof gate (required after edits) | [references/verification-before-completion.md](references/verification-before-completion.md) | Fresh terminal output after final edit |
| PR diff audit, OWASP/perf severity review (`P0`–`P3`) | [references/code-review-and-checklist.md](references/code-review-and-checklist.md) | Read-only review; severity matrix & YAGNI filter |
| Clean up nested/heavy working code safely | [references/code-simplification.md](references/code-simplification.md) | Preserve exact behavior; Chesterton's Fence |
| Adversarial cross-exam on high-stakes decisions | [references/doubt-driven-development.md](references/doubt-driven-development.md) | Fresh-context `invoke_subagent` (`ARTIFACT` + `CONTRACT`) |

> **Cross-Skill Contract:** Prune single-line test/diff runs with `rtk` (`token-and-context-ops`), escalate auth/IDOR/CSP/SSRF/secret findings to `cyber-security-analyst`, and prefer `chrome-devtools-plugin` for live browser heap snapshots.
