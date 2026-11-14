# Cyber Security & Threat Analyst Protocol

Core defensive standards for vulnerability triage, cryptographic selection, network anomaly detection, and authorization auditing.

## 1. Cryptography & Credential Storage
- Enforce `Argon2id` or `bcrypt` (work factor $\ge 12$) for password storage; block MD5, SHA-1, and unsalted hashes.
- Use authenticated encryption (`AES-256-GCM` or `ChaCha20-Poly1305`) for data at rest.

## 2. Network Security & Packet Inspection
- Apply Wireshark/TShark display filters to detect port scans, DNS tunneling, and cleartext credential leaks (see [penetration-testing-and-crypto.md](penetration-testing-and-crypto.md)).

## 3. Defensive Authorization (BOLA / IDOR Prevention)
- Never trust object IDs from request bodies, query params, or URLs without binding queries to the authenticated caller's `ownerUserId` or RBAC policy.

## 4. Verification Gate
- After fixing authorization or cryptographic logic, execute both positive (authorized user) and negative (`401`/`403` cross-user token) security tests before claiming completion (`quality-testing-review` (`references/verification-before-completion.md`)).
