---
name: backend-and-sql
description: Use when building REST APIs (Node/Go/Python/Java), designing PostgreSQL/MySQL/SQLite schemas and migrations, optimizing SQL queries, or writing Go concurrent services and Java Spring Boot 3 backends.
---

# Backend Architecture, Databases, Go & Spring Boot

Load only the stack guide needed for the current module:

| Stack / Domain | Reference Guide | Key Topics |
| :--- | :--- | :--- |
| REST API, JWT/OAuth2, Zod/DTO validation, Idempotency | [references/rest-api-and-resilience.md](references/rest-api-and-resilience.md) | `HttpOnly` cookies, RFC status codes, 4xx/2xx gate |
| PostgreSQL/MySQL/SQLite schemas, indexes, transactions | [references/sql-and-transactions.md](references/sql-and-transactions.md) | 3NF, B-Tree/GIN, `CONCURRENTLY`, `EXPLAIN ANALYZE` |
| Go services, goroutines, worker pools, `log/slog`, shutdown | [references/golang-concurrency.md](references/golang-concurrency.md) | `%w` errors, `context.Context`, `go test -race` |
| Java 17/21, Spring Boot 3, Virtual Threads, JPA/Hibernate | [references/java-spring-boot.md](references/java-spring-boot.md) | DTO `record`, `JOIN FETCH` N+1 fix, RFC 7807 |
