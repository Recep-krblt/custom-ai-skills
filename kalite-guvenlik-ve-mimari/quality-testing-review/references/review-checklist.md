# Senior Code Review & Security Audit Checklist

## 1. Severity Matrix

* **P0 - Blocker (Release Stopper):**
  - Security vulnerabilities (SQL Injection, XSS, SSRF, auth bypass, IDOR).
  - Runtime crashes (uncaught exceptions, null pointer dereferences, deadlocks).
  - Data loss or irreversible corruption risks.
* **P1 - Major (Architecture & Performance Bottleneck):**
  - Database N+1 queries or missing indexes.
  - Synchronous I/O blocking the event loop.
  - Unclosed DB connections, file handles, or memory leaks.
* **P2 - Minor (Clean Code & Maintainability):**
  - Single-Responsibility Principle (SRP) violations.
  - Insufficient test coverage or flaky tests.
  - Obscure naming, dead code, or leftover `TODO`s.
* **P3 - Nitpick (Style & Preference):**
  - Docstring formatting, variable ordering, or minor stylistic suggestions.

---

## 2. Concurrency & Security Deep Checks

### A. Concurrency & Async Flow
- Are independent promises awaited sequentially instead of using `Promise.all` (async waterfall)?
- Does shared state have race conditions or missing lock synchronization?
- Do background tasks have proper error handling (`try/catch` or rejection handlers)?

### B. OWASP & Secret Hygiene
- Is user input passed into shell commands (`exec`, `system`) or `eval`?
- Are secrets, API keys, or PII written to logs?
- Are CORS/CSRF policies misconfigured (e.g., `Access-Control-Allow-Origin: *` with `credentials: true`)?

---

## 3. Finding Report Template

```markdown
### [P0 - Blocker] SQL Injection Risk
- **File:** `src/services/user.service.ts#L42-L46`
- **Rationale:** User-supplied `searchQuery` is interpolated directly into a raw SQL string.
- **Targeted Diff:**
```ts
// Before
const users = await db.query(`SELECT * FROM users WHERE name LIKE '%${query}%'`);

// After (Parameterized)
const users = await db.query('SELECT * FROM users WHERE name LIKE $1', [`%${query}%`]);
```
```

---

## 4. Receiving Review Feedback Protocol
When evaluating review comments from another agent or developer:
1. **No Performative Agreement:** Skip "Great catch! / You're absolutely right!" filler; verify technically or provide concrete counter-evidence.
2. **Verify Against the Codebase First:** Check whether the suggestion breaks existing callers, backward compatibility, or platform constraints (Windows/POSIX) before applying it.
3. **YAGNI Filter:** If a comment suggests adding speculative abstractions ("might need later"), search for actual usage (`grep` / `repo-map --find`) and reject unused complexity.
4. **Incremental Verification:** Apply fixes starting from P0 blockers and re-run tests after each change.
