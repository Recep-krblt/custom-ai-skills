# Test-Driven Development (TDD), Mocking & Anti-Hang Protocol

## 1. Red-Green-Refactor Workflow & Pyramid
1. **Red:** Write a failing test defining expected behavior before production code.
2. **Watch-RED-Fail:** Run the test and confirm it fails because the feature is missing (not syntax/import errors).
3. **Green:** Write the minimal production code required to pass the test.
4. **Refactor:** Clean up duplication and tighten types while keeping tests green.
- **Test Pyramid:** Target ~70% fast unit tests (`< 10 ms`, pure logic + boundary mocks), ~20% integration tests (real DB/Testcontainers, queues, HTTP middleware), and ~10% E2E tests (critical user journeys).

## 2. Mandatory Edge-Case Matrix
Cover these boundaries for every non-trivial function:
1. **Empty / Null Inputs:** `""`, `null` / `None`, `undefined`, `[]`, `{}`.
2. **Boundary Values:** $0$, $-1$, `MAX_SAFE_INTEGER`, numeric overflow/underflow.
3. **Time & Timezones:** Leap years, UTC vs local offsets, midnight rollovers.
4. **Network & Timeouts:** Unresponsive upstreams, malformed responses, slow DB queries.

## 3. Resilient Boundary Mocking & Anti-Patterns
- **Mock Only External I/O Boundaries:** Stub HTTP gateways, payment providers, queues, or mailers via interfaces; keep domain logic, SQL queries (integration tests), and serializers real:
  ```typescript
  const mockStripe = { charge: vi.fn(), refund: vi.fn() } as unknown as StripeGateway;
  vi.mocked(mockStripe.charge).mockResolvedValue({ success: true, transactionId: 'tx_123' });
  const result = await new PaymentService(mockStripe).processOrder('ord_99', 500);
  expect(result.status).toBe('COMPLETED');
  ```
- **Avoid Anti-Patterns:**
  - *Testing Mock Internals:* Asserting `toHaveBeenCalled()` alone without checking return values or state transitions.
  - *Anti-Mirror Assertions:* Copying production math/formulas into expectations instead of asserting against independent hand-computed values.
  - *Test-Only Production Backdoors:* Adding `_resetForTest()` methods to production classes instead of cleaning up in test fixtures.
  - *Arbitrary `sleep()` / `setTimeout()` Delays:* Poll for conditions instead (see [condition-based-waiting.md](condition-based-waiting.md)).

## 4. Anti-Hang & Timeout Protection Protocol
Prevent test runners from hanging indefinitely:
- **Never Run Watch Mode Bare:**
  - **Vitest:** `npx vitest run` (bare `vitest` blocks forever in watch mode).
  - **Jest:** `CI=true npx jest --watchAll=false --forceExit`.
  - **Pytest:** `pytest -q --timeout=30` or `pytest -o faulthandler_timeout=30`.
  - **Go:** `go test -timeout 30s ./...`.
- **Close Open Handles:** Always close HTTP servers (`server.close()`), DB pools (`pool.end()`, `prisma.$disconnect()`), and listeners in `afterAll` / teardown fixtures.
- **Universal Watchdog Wrapper:** Wrap commands that risk infinite loops or async deadlocks with [../scripts/run_with_timeout.py](../scripts/run_with_timeout.py):
  ```powershell
  python "<SKILLS_DIR>/quality-testing-review/scripts/run_with_timeout.py" --timeout 30 "<test-command>"
  ```
