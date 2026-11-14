# Defensive Application Hardening & Secret Hygiene

Synthesized strictly for defensive architecture review, boundary validation, supply-chain triage, and pre-release secret hygiene.

## 1. Threat Model Before Writing Controls (STRIDE)

1. **Map Trust Boundaries:** HTTP requests, query params, webhooks, uploaded files, CLI args/env from other processes, third-party API payloads, and **LLM/model outputs**. Trust follows who *wrote* a value, not the transport channel.
2. **Identify High-Value Assets:** Credentials, session cookies, PII, billing/payment records, admin actions.
3. **Check STRIDE Per Boundary:** Spoofing (authn/signatures), Tampering (parameterized queries/HTTPS), Repudiation (audit logs), Information Disclosure (allowlisted DTO fields/generic errors), Denial of Service (rate limits/timeouts/size caps), Elevation of Privilege (per-resource authz).

## 2. Boundary Controls Checklist

- **Injection & Queries:** Parameterize every SQL/NoSQL/ORM query; never build shell strings or `eval` from inputs or LLM text.
- **Authorization (BOLA/IDOR):** Verify resource ownership (`ownerId == authenticatedUser.id` or RBAC policy) on every handler after authentication.
- **Authentication & Sessions:** Hash passwords with Argon2id or bcrypt (cost >= 12); load signing/session secrets strictly from environment variables; issue `HttpOnly`, `Secure`, `SameSite=Lax|Strict` cookies with bounded TTLs.
- **Rate Limiting:** Restrict auth endpoints strictly; back limiters with a shared store (e.g., Redis) when running multiple instances.
- **SSRF Defense:** When the server fetches user-influenced URLs, allowlist `https:` + approved hosts, resolve DNS and block loopback/private/link-local (`169.254.169.254` / IPv6 ULA) addresses, and disable automatic redirects.
- **Derived Filesystem Paths (Delete/Move/Overwrite):** Resolve symlinks (`realpath`/`Path.resolve()`), require the resolved target to stay strictly **below** an allowlisted root directory, verify ownership before operating, and fail closed without falling back to broader paths.
- **Uploads:** Allowlist MIME types, enforce byte size caps, inspect magic bytes, and store outside executable web roots.
- **AI / LLM Features:** Treat model output as untrusted data (`JSON.parse` + schema validation + context-appropriate escaping); never place secrets, cross-tenant data, or admin credentials inside prompt context; require explicit confirmation for destructive tools.

## 3. Supply-Chain & Lockfile Hygiene

1. Keep a single authoritative lockfile per workspace boundary and commit it.
2. Disable or inspect dependency post-install lifecycle scripts before approving new packages.
3. Run native package manager audits (`npm audit`, `pip-audit`, `govulncheck`) against the lockfile before releases, triaging findings by actual code reachability (never auto-run blind `--force` major bumps without inspecting diffs/tests).
4. Guard against typosquatting by verifying package ownership, release age, and lockfile diffs on new additions.

## 4. Defensive Pre-Commit & Client-Bundle Secret Hygiene

Prevent accidental credential exposure in source control, CI logs, or browser bundles:
- **Environment Isolation:** Keep `.env` / private keys / certs in `.gitignore`; commit only `.env.example` with empty or clearly synthetic placeholders (`CHANGE_ME`).
- **Client vs Server Separation:** In Astro/Vite/Next.js builds, confirm only explicitly non-sensitive configuration uses `PUBLIC_*` / `NEXT_PUBLIC_*`. Never interpolate server-side env vars into inline scripts, HTML `meta` tags, `data-*` attributes, comments, or serialized JSON props sent to the browser.
- **Public Webroot Exclusion:** Configure Nginx/Docker/static hosts so `.git/`, `.env*`, `.dockerignore`, config dumps, backups, and uncompiled source directories are never packaged or served statically (`dist/` artifacts only).
- **Safe Local Diff Review:** Before pushing, scan staged diffs and build output (`frontend/dist/` or `git diff --cached --name-only`) locally; print only **file path + line number + secret type** (never echo candidate credential values into shared terminal logs or LLM context).
- **Incident Response:** If a real credential ever reaches a remote commit, **revoke and rotate the secret immediately first**, then scrub repository history.

## 5. Personal Data Minimization (Privacy by Design)

- Classify collected fields (public, PII, sensitive); collect only what has a documented purpose and defined TTL/retention policy.
- Exclude PII and auth tokens from debug logs, error payloads, stack traces, and telemetry.
- Ensure account deletion removes or anonymizes backups/caches/indexes rather than leaving orphan PII behind.
