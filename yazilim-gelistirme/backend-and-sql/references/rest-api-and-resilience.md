# REST API & Resilient Backend Architecture

Standards for secure, fault-tolerant RESTful services across Node.js, Go, Python, and Java.

## 1. REST Resource Naming & HTTP Semantics
- Use plural nouns in paths, never verbs (`GET /api/v1/orders`, `POST /api/v1/orders`).
- Standardize status codes: `200`/`201`/`204` (success), `422` (validation failure), `401`/`403` (auth/authz), `404` (not found), `429` (rate limit exceeded).
- Validate all incoming payloads with strict schemas (Zod, Joi, Pydantic, Class-Validator) before business logic.
- Return predictable structured error envelopes (`code`, `message`, `details`, `requestId`).

## 2. Idempotency Pattern (Critical Mutations)
Prevent duplicate payments, transfers, or order creation on retries:
- Require `Idempotency-Key: <UUID>` header on mutating `POST` endpoints.
- Lock the key in Redis with a TTL (`SET key payload NX EX 86400`).
- Cache the completed response in Redis; return the stored `200 OK` / `201 Created` payload directly on subsequent requests with the same key.

## 3. Refresh Token Rotation & Reuse Detection
- Never store JWTs in `localStorage`; use `HttpOnly, Secure, SameSite=Strict` cookies.
- Rotate the refresh token on every token refresh request and invalidate the previous token.
- **Reuse Detection:** If a previously invalidated refresh token is presented again, treat it as token theft and immediately revoke all active sessions/refresh tokens for that user.

## 4. Distributed Tracing & Rate Limiting
- Capture incoming `X-Request-Id` (or generate a UUID) and attach it to every response header and structured log entry:
  ```json
  {
    "timestamp": "2026-11-05T21:03:00Z",
    "level": "INFO",
    "requestId": "a8f3c7e9-2b41-4c6e-9e8a-028a427f71b2",
    "message": "order created",
    "userId": "usr_9912"
  }
  ```
- Enforce token-bucket rate limiting by IP and user ID; return `429 Too Many Requests` with a `Retry-After: <seconds>` header.

## 5. Verification Gate
- After endpoint or schema edits, run integration tests covering both valid (`2xx`) and invalid/unauthorized (`4xx`) requests (`quality-testing-review` (`references/verification-before-completion.md`)).
