# Test-Driven Development (TDD) & Anti-Hang Protocol

## 1. Red-Green-Refactor Workflow
1. **Red:** Write a failing test defining the expected behavior before writing implementation code.
2. **Watch-RED-Fail:** Run the test and confirm it fails because the feature is missing (not due to syntax/import errors).
3. **Green:** Write the minimal production code required to pass the test.
4. **Refactor:** Clean up duplication (DRY) and tighten types while keeping tests green.

## 2. Resilient Mocking & Anti-Patterns
- Mock only external I/O boundaries (HTTP APIs, payment gateways, email providers) via interfaces; see [testing-patterns.md](testing-patterns.md).
- Test real system behavior rather than mock call counts; avoid anti-mirror assertions (copying production formulas into expectations) and test-only methods in production classes.
- Replace arbitrary `sleep()` / `setTimeout()` delays with condition-based polling (see [condition-based-waiting.md](condition-based-waiting.md)).

## 3. Anti-Hang & Timeout Protection Protocol
Prevent test runners from hanging indefinitely:
- **Never Run Watch Mode Bare:**
  - **Vitest:** `npx vitest run` (bare `vitest` blocks forever in watch mode).
  - **Jest:** `CI=true npx jest --watchAll=false --forceExit`.
  - **Pytest:** `pytest -q --timeout=30` or `pytest -o faulthandler_timeout=30`.
  - **Go:** `go test -timeout 30s ./...`.
- **Close Open Handles:** Always close HTTP servers (`server.close()`), DB pools (`pool.end()`, `prisma.$disconnect()`), and listeners in `afterAll` / teardown fixtures.
- **Universal Watchdog Wrapper:** Wrap commands that risk infinite loops or async deadlocks with [../scripts/run_with_timeout.py](../scripts/run_with_timeout.py):
  ```powershell
  python "C:\Users\<USERNAME>\.gemini\config\skills\quality-testing-review\scripts\run_with_timeout.py" --timeout 30 "<test-command>"
  ```
