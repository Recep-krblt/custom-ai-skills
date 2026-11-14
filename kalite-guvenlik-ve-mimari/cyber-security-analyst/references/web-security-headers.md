# Web Security Headers, XSS Sanitization & CSRF Defense

## 1. Mandatory HTTP Security Headers Baseline

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-rAnd0m123'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self';
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

---

## 2. XSS Defense & HTML Sanitization (DOMPurify)

When rendering user-supplied HTML is unavoidable, sanitize with an explicit tag/attribute allowlist:
```typescript
import DOMPurify from 'dompurify';

export function sanitizeHTML(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'li', 'code'],
    ALLOWED_ATTR: ['href', 'title', 'target'],
    ALLOW_DATA_ATTR: false
  });
}
```

---

## 3. CSRF (Cross-Site Request Forgery) Defense
- **SameSite Cookies:** Enforce `SameSite=Lax` or `SameSite=Strict` alongside `HttpOnly` and `Secure`.
- **CSRF Tokens:** Validate an anti-CSRF header (`X-CSRF-Token`) on all state-mutating (`POST`, `PUT`, `PATCH`, `DELETE`) cookie-authenticated endpoints.
