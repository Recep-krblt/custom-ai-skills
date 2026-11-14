# SQL Schema Design, Indexing & Zero-Downtime Migrations

Standards for relational integrity, query optimization, deadlock prevention, and lock-safe migrations in PostgreSQL, MySQL, and SQLite.

## 1. Schema Integrity & Query Optimization
- Enforce 1NF/2NF/3NF normalization and explicit `ON DELETE CASCADE / RESTRICT` constraints on M:N junction tables.
- Never use `= NULL`; always use `IS NULL` / `IS NOT NULL`.
- Avoid `SELECT *` on large tables; project only required columns.

## 2. Composite Indexing (Leftmost Prefix) & GIN
```sql
CREATE INDEX idx_orders_user_status ON orders (user_id, status, created_at DESC);
```
- **Uses Index:** `WHERE user_id = 5`, `WHERE user_id = 5 AND status = 'COMPLETED'`, `WHERE user_id = 5 AND status = 'COMPLETED' ORDER BY created_at DESC`.
- **Misses Index (Seq Scan):** `WHERE status = 'COMPLETED'` (leading column omitted).
- **PostgreSQL JSONB / Array GIN Index:**
  ```sql
  CREATE INDEX idx_products_tags ON products USING GIN (tags);
  CREATE INDEX idx_metadata_gin ON users USING GIN (metadata jsonb_path_ops);
  ```

## 3. Deadlock Prevention: Deterministic Lock Ordering
When updating multiple rows inside a transaction, always acquire row locks in ascending ID order:
```sql
BEGIN;
SELECT * FROM accounts WHERE id IN (10, 20) ORDER BY id FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 10;
UPDATE accounts SET balance = balance + 100 WHERE id = 20;
COMMIT;
```

## 4. Zero-Downtime Schema Migrations
Avoid exclusive table locks in production:
- **Index Creation:** Always use `CREATE INDEX CONCURRENTLY` (PostgreSQL).
- **Adding `NOT NULL` Columns Safely:**
  1. Add nullable column: `ALTER TABLE users ADD COLUMN is_active boolean DEFAULT true;`
  2. Backfill existing rows in small batches.
  3. Add unvalidated constraint: `ALTER TABLE users ADD CONSTRAINT check_is_active CHECK (is_active IS NOT NULL) NOT VALID;`
  4. Validate constraint without blocking writes: `ALTER TABLE users VALIDATE CONSTRAINT check_is_active;`

## 5. Verification Gate
- Inspect `EXPLAIN ANALYZE` plans (confirming Index Scan over Seq Scan) and test migration rollback paths before claiming completion (`quality-testing-review` (`references/verification-before-completion.md`)).
