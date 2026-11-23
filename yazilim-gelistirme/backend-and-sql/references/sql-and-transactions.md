# SQL Schema Design, Indexing & Zero-Downtime Migrations

Standards for relational integrity, PostgreSQL table design, query optimization, deadlock prevention, and lock-safe migrations across PostgreSQL, MySQL, and SQLite.

## 1. Schema Integrity & PostgreSQL Type Hygiene
- Enforce 1NF/2NF/3NF normalization first; denormalize only for measured, high-ROI read paths.
- Specify explicit foreign-key actions (`ON DELETE CASCADE / RESTRICT / SET NULL`) and **manually index FK referencing columns** (PostgreSQL does not auto-index FK columns).
- Never compare with `= NULL`; always use `IS NULL` / `IS NOT NULL`. Avoid `SELECT *` on wide tables.
- **Preferred PostgreSQL Column Types:**
  - **Primary Keys:** Prefer `BIGINT GENERATED ALWAYS AS IDENTITY` over legacy `serial`; use `UUID` (`gen_random_uuid()` / PG18+ `uuidv7()`) only when globally unique/opaque IDs are required.
  - **Time, Numbers & Text:** Use `TIMESTAMPTZ` (never bare `timestamp`), `NUMERIC(p,s)` for money (never `money`/`float`), `TEXT` + `CHECK (LENGTH(col) <= n)` over `varchar(n)`/`char(n)`, and `JSONB` (not `json`) only for semi-structured attributes. Use `TEXT` + `CHECK` (or lookup tables) instead of `ENUM` for evolving business values.
- **Constraints:**
  - `UNIQUE NULLS NOT DISTINCT` (PG15+) when at most one `NULL` should be allowed.
  - Combine `CHECK` constraints with `NOT NULL` because `NULL` satisfies `CHECK` under three-valued logic.
  - Use `EXCLUDE USING gist (...)` (e.g., `room_id WITH =, booking_period WITH &&`) to enforce non-overlapping intervals at the database level.

## 2. Indexing & Declarative Partitioning
```sql
CREATE INDEX idx_orders_user_status ON orders (user_id, status, created_at DESC);
```
- **Composite Index (Leftmost Prefix):** `WHERE user_id = 5 AND status = 'COMPLETED'` uses the index; omitting `user_id` triggers a Seq Scan. Put equality predicates before range/sort columns.
- **Specialized PostgreSQL Index Patterns:**
  - **Covering:** `CREATE INDEX ON tbl (id) INCLUDE (name, email)` enables index-only scans.
  - **Partial:** `CREATE INDEX ON tbl (user_id) WHERE status = 'active'` keeps hot subsets compact.
  - **Expression:** `CREATE UNIQUE INDEX ON users (LOWER(email))` matches expression lookups.
  - **GIN / BRIN:** Use GIN (`jsonb_path_ops` or array ops) for JSONB/arrays/full-text; use BRIN for huge, naturally append-only time-series tables.
- **Declarative Partitioning (>100M rows):** Prefer native `PARTITION BY RANGE / LIST / HASH` over table inheritance; include the partition key in every `PRIMARY KEY` / `UNIQUE` constraint.

## 3. Deadlock Prevention & Lock-Safe Queues
When updating multiple rows inside a transaction, always acquire locks in deterministic ascending key order:
```sql
BEGIN;
SELECT * FROM accounts WHERE id IN (10, 20) ORDER BY id FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 10;
UPDATE accounts SET balance = balance + 100 WHERE id = 20;
COMMIT;
```
- Use `FOR UPDATE SKIP LOCKED` when polling worker/job queues to prevent lock contention across workers.

## 4. Zero-Downtime Schema Migrations
Avoid exclusive table locks in production:
- **Index Creation:** Always use `CREATE INDEX CONCURRENTLY` (PostgreSQL).
- **Adding `NOT NULL` Columns Safely:**
  1. Add nullable column with default: `ALTER TABLE users ADD COLUMN is_active boolean DEFAULT true;`
  2. Backfill existing rows in small batches.
  3. Add unvalidated constraint: `ALTER TABLE users ADD CONSTRAINT check_is_active CHECK (is_active IS NOT NULL) NOT VALID;`
  4. Validate without blocking writes: `ALTER TABLE users VALIDATE CONSTRAINT check_is_active;`

## 5. Verification Gate
- Inspect `EXPLAIN ANALYZE` plans (confirming Index Scan / Index-Only Scan over unexpected Seq Scan) and test migration rollback paths before claiming completion (`quality-testing-review` (`references/verification-before-completion.md`)).
