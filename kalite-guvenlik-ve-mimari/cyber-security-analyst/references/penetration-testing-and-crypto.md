# Cryptography, Network Traffic & BOLA/IDOR Defense Guide

## 1. Modern Cryptography & Password Storage Standards

* **Password Hashing:**
  - **Primary (Memory-Hard):** `Argon2id` (memory: 64 MB, iterations: 3, parallelism: 4).
  - **Secondary (Industry Standard):** `bcrypt` (work factor $\ge 12$).
  - **Strictly Forbidden:** MD5, SHA-1, unsalted SHA-256.
* **Symmetric Encryption at Rest (AEAD Mandatory):**
  - `AES-256-GCM` or `ChaCha20-Poly1305` (never use unauthenticated AES-CBC or ECB).

---

## 2. Network Traffic & Protocol Analysis (Wireshark / TShark Filters)

* **SYN Flood / Port Scan Detection:**
  `tcp.flags.syn == 1 and tcp.flags.ack == 0`
* **Cleartext Credential Exposure:**
  `http.request.method == "POST" and (http contains "password" or http contains "token")`
* **DNS Tunneling / Suspicious TXT Queries:**
  `dns.flags.response == 0 and dns.qry.type == 16`

---

## 3. Object-Level Authorization (BOLA / IDOR) Verification
- Never query database records solely by a client-supplied `id` parameter.
- Bind every resource query to the authenticated session user's ownership (`ownerUserId`):
  ```typescript
  const document = await db.documents.findFirst({
    where: {
      id: documentId,
      ownerUserId: session.user.id // Prevents BOLA/IDOR at the query boundary
    }
  });
  ```
