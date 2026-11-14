---
name: cyber-security-analyst
description: Use when auditing authentication/authorization (BOLA/IDOR), reviewing cryptography/network captures, threat modeling input boundaries/SSRF/file paths, or enforcing secret-exposure and dependency hygiene.
---

# Cyber Security Analyst & Defensive Hardening

Treat every external input and LLM output as untrusted, every secret as environment-only, and every access check as mandatory:

| Focus Area | Reference Guide | Notes |
| :--- | :--- | :--- |
| Threat modeling, crypto (Argon2id/AEAD), BOLA/IDOR, negative tests | [references/security-analyst-protocol.md](references/security-analyst-protocol.md) | Core defensive protocols |
| Packet filters, crypto parameters, pentest verification | [references/penetration-testing-and-crypto.md](references/penetration-testing-and-crypto.md) | Wireshark/TShark & AEAD |
| HTTP security headers, CSP, CORS, cookies & edge hygiene | [references/web-security-headers.md](references/web-security-headers.md) | Strict headers & CSRF defaults |
| OWASP hardening, SSRF, supply chain, LLM safety & secret hygiene | [references/security-hardening-and-secret-hygiene.md](references/security-hardening-and-secret-hygiene.md) | Defensive boundary & `.env`/bundle checks |
