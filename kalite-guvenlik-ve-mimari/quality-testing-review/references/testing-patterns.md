# Testing Pyramid, Mocking & Edge-Case Matrix

## 1. Test Pyramid & Coverage Strategy
* **Unit Tests (70%):** Pure functions and isolated domain logic with external I/O mocked (`< 10 ms` per test).
* **Integration Tests (20%):** Database (Testcontainers), Redis, external API boundaries, and middleware pipelines.
* **End-to-End (E2E) Tests (10%):** Critical user journeys via Playwright / Cypress (login, checkout).

---

## 2. Resilient Boundary Mocking (Vitest / Jest)

```typescript
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { PaymentService } from './payment.service';
import { StripeGateway } from '../gateways/stripe.gateway';

describe('PaymentService (TDD)', () => {
  let paymentService: PaymentService;
  let mockStripe: StripeGateway;

  beforeEach(() => {
    mockStripe = {
      charge: vi.fn(),
      refund: vi.fn(),
    } as unknown as StripeGateway;

    paymentService = new PaymentService(mockStripe);
  });

  it('marks order as COMPLETED on successful charge', async () => {
    vi.mocked(mockStripe.charge).mockResolvedValue({ success: true, transactionId: 'tx_123' });

    const result = await paymentService.processOrder('ord_99', 500);

    expect(result.status).toBe('COMPLETED');
    expect(result.transactionId).toBe('tx_123');
    expect(mockStripe.charge).toHaveBeenCalledWith(500, 'USD');
  });

  it('throws and fails order when payment gateway times out', async () => {
    vi.mocked(mockStripe.charge).mockRejectedValue(new Error('Stripe timeout'));

    await expect(paymentService.processOrder('ord_99', 500)).rejects.toThrow('Stripe timeout');
  });
});
```

---

## 3. Mandatory Edge-Case Matrix
Cover these boundaries for every non-trivial function:
1. **Empty / Null Inputs:** `""`, `null`, `undefined`, `[]`, `{}`.
2. **Boundary Values:** $0$, $-1$, `Number.MAX_SAFE_INTEGER`, numeric overflow.
3. **Time & Timezones:** Leap years, UTC vs local offsets, midnight rollovers.
4. **Network & Timeouts:** Unresponsive upstream services, slow DB queries.

---

## 4. Test Anti-Patterns
- **Testing Mock Internals:** `expect(mockFn).toHaveBeenCalled()` alone is insufficient; assert the real return value or state transition and mock only external I/O boundaries.
- **Test-Only Methods in Production Code:** Never add `_resetForTest()` backdoors to production classes; manage cleanup in test fixtures.
- **Anti-Mirror Assertions:** Assert against hand-computed constants rather than duplicating the production formula inside the test.
- **No Arbitrary `sleep()`:** Poll for the target condition (`waitFor`) instead of using fixed timers.
