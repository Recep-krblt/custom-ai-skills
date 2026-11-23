# Code Review & Security Audit Checklist

## 1. Severity Prioritization Matrix
Group all findings by severity:
1. **P0 (Blocker / Release Stopper):** Security vulnerabilities (SQLi, XSS, SSRF, auth bypass, IDOR), runtime crashes (uncaught exceptions, null pointer dereferences, deadlocks), memory leaks, data loss/corruption.
2. **P1 (Major / Architecture & Performance):** DB N+1 queries or missing indexes, synchronous I/O blocking an event loop or virtual-thread carrier, async waterfalls (`await` in sequence vs parallel), unclosed handles/connections.
3. **P2 (Minor / Clean Code & Maintainability):** Single-Responsibility Principle (SRP) violations, insufficient edge-case tests, flaky tests, code duplication (DRY), dead code.
4. **P3 (Nitpick):** Naming, docstring formatting, or stylistic preferences.

## 2. Two-Stage Review & Read-Only Discipline
- **Read-Only Audit:** Do not mutate source code during a review unless explicitly asked to apply fixes; report diagnosis, `file#Lx-Ly` evidence, and targeted diffs.
- **Spec Compliance First, Code Quality Second:** Verify requirements and acceptance criteria before auditing architecture, concurrency, and security.
- **Surgical Findings Format:** Every finding must include Severity, `File#Lx-Ly`, Rationale, and Targeted Diff:
  ```markdown
  ### [P0 - Blocker] SQL Injection Risk
  - **File:** `src/services/user.service.ts#L42-L46`
  - **Rationale:** User-supplied `searchQuery` is interpolated directly into raw SQL.
  - **Targeted Diff:** Replace string interpolation with parameterized query `$1`.
  ```

## 3. Concurrency & OWASP Deep Checks
- **Concurrency & Async Flow:** Flag sequential awaits on independent I/O, unsynchronized shared mutable state, and background tasks missing error/rejection handlers.
- **Security & Secret Hygiene:** Flag shell command string interpolation (`exec`/`system`/`shell=True`), `eval`, secrets/PII written to logs, and unsafe CORS (`Access-Control-Allow-Origin: *` with `credentials: true`).

## 4. Receiving Review Feedback Protocol
When evaluating review comments from another agent or developer:
1. **No Performative Agreement:** Skip conversational filler; verify technically or supply concrete counter-evidence.
2. **Verify Against the Codebase First:** Check whether the suggestion breaks existing callers, backward compatibility, or OS constraints (Windows/POSIX) before applying it.
3. **YAGNI Filter:** Reject speculative abstractions ("might need later") unless callers actually use them (`repo-map --find` / `grep`).
4. **Incremental Verification:** Apply fixes starting from `P0` blockers and re-run the test suite after each change (`references/verification-before-completion.md`).
