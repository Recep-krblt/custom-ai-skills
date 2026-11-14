# Verification Before Completion

Claiming work is done without fresh verification output is a defect. Evidence precedes assertions, always.

**Iron Law:**
```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

## The Five-Step Verification Gate

Before stating ANY status claim ("tests pass", "bug fixed", "build clean", "lint passes", "script works"):

1. **IDENTIFY:** Which exact command proves the claim? (Not a proxy, not a subset unless explicitly scoped.)
2. **RUN:** Execute the **full** command via `run_command` **after your final edit**.
3. **READ:** Inspect the actual exit code, pass/fail counts, skipped/xfail counts, and stderr/warnings — never rely on memory or earlier runs before the last edit.
4. **VERIFY:** Confirm the output matches every part of your claim (no relaxed assertions, no filtered-only pass masquerading as full suite pass).
5. **ONLY THEN CLAIM:** State what you directly observed, with exact command, scope, and counts.

Skip any step = unverified claim.

## Verification Standards by Claim Type

| Claim | Required Proof | Insufficient |
| --- | --- | --- |
| Tests pass | Test command output after final edit: 0 failed, exact N/N passed | Previous run, mocked-only run, linter pass, "should pass" |
| Build succeeds | Build command exits 0 after final edit | Typecheck only, IDE squiggles clear |
| Bug fixed | Original failing reproduction test/command now passes + regression suite runs cleanly | Only reading code and inferring fix works |
| UI / Web flow works | Live browser/Playwright check (`web-frontend-suite` (`references/playwright-webapp-testing.md`) or `browser` subagent) verifying rendered DOM + zero console/5xx errors | Static code review or `curl 200` on SSR shell |
| Script / CLI works | Real execution (`python script.py ...`, `--help`, fixture run) exiting 0 | `py_compile` or syntax check alone |
| Files / skills valid | Validator/check script run over target directory reporting 0 errors | Inspecting a single file manually |

## Anti-Rationalization Rules

Stop immediately if you catch yourself thinking:
- *"It's a trivial one-line comment/import change, no need to re-run."* → Re-run anyway; trivial edits break builds and imports constantly.
- *"I'm confident the logic is right."* → Confidence is not tool output.
- *"I ran the tests 2 edits ago."* → Those results are stale.
- *"The linter/compiler passed, so runtime is fine."* → Compilers do not verify runtime behavior.
- *"Only 1 test was skipped / failed in an unrelated area."* → Report exact skipped/failed counts and scope explicitly; never report "all tests pass".

## Partial Verification Disclosure

When full verification is genuinely impossible in the environment (e.g., missing credentials, hardware device, or blocked external service), state explicitly:
- **Verified:** exact commands executed and exact outputs observed.
- **Unverified / Blocked:** exact gap and why it could not be run.

Never extrapolate partial or mocked checks into full completion claims.
