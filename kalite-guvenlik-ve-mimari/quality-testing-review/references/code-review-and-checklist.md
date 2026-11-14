# Code Review & Security Audit Methodology

## 1. Severity Prioritization Matrix
Group all findings by severity:
1. **P0 (Blocker):** Security vulnerabilities (SQLi, XSS, SSRF, IDOR), memory leaks, data loss/corruption, crashes.
2. **P1 (Major):** Performance bottlenecks (N+1 queries, event-loop blocking, async waterfalls), unclosed handles/resources.
3. **P2 (Minor):** SRP violations, missing edge-case tests, code duplication (DRY).
4. **P3 (Nitpick):** Naming and formatting preferences.

See [review-checklist.md](review-checklist.md) for the detailed checklist and report template.

## 2. Two-Stage Review & Read-Only Discipline
- **Read-Only Audit:** Do not mutate source code during a review unless explicitly asked to apply fixes; report diagnosis, `file#Lx-Ly` evidence, and targeted diffs.
- **Spec Compliance First, Code Quality Second:** Verify all requirements and acceptance criteria are met before auditing security, performance, and architecture.
- **Surgical Findings:** Every finding must include **Severity (`P0/P1/P2`)**, **File & Line (`file#Lx-Ly`)**, **Technical Rationale**, and **Targeted Diff**.
- **Receiving Review Feedback:** Verify reviewer suggestions against the actual codebase and YAGNI principles rather than agreeing performatively (see [review-checklist.md](review-checklist.md)); run the verification gate (`references/verification-before-completion.md`) after applying fixes.
