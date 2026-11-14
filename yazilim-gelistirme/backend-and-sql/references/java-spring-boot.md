# Java 21 & Spring Boot 3 Enterprise Architecture

Standards for type-safe, high-throughput Spring Boot 3 backends free of JPA N+1 bottlenecks.

## Core Principles

1. **Modern Java & Constructor Injection:**
   - Use immutable `record` classes for DTOs instead of verbose getter/setter classes.
   - Never use `@Autowired` field injection; use constructor injection (`@RequiredArgsConstructor`).
2. **JPA/Hibernate Performance & N+1 Prevention:**
   - Prevent N+1 queries on associations via `JOIN FETCH` or `@EntityGraph`.
   - Annotate read-only service methods with `@Transactional(readOnly = true)` to skip Hibernate dirty checking.
3. **Virtual Threads & Validation:**
   - Enable Java 21+ virtual threads (`spring.threads.virtual.enabled=true`) and avoid blocking I/O inside `synchronized` blocks (use `ReentrantLock` to prevent carrier thread pinning).
   - Validate all HTTP request bodies with `@Valid`.
4. **Verification Gate:**
   - Run `./mvnw test` or `.\gradlew.bat test` after edits to verify all JUnit 5/integration tests pass and query counts do not regress (`quality-testing-review` (`references/verification-before-completion.md`)).

---

## 1. JPA N+1 Prevention (`JOIN FETCH` & `@EntityGraph`)

```java
public interface OrderRepository extends JpaRepository<Order, UUID> {
    @Query("SELECT o FROM Order o JOIN FETCH o.customer WHERE o.status = :status")
    List<Order> findAllByStatusWithCustomer(@Param("status") OrderStatus status);

    @EntityGraph(attributePaths = {"customer", "items"})
    List<Order> findByCreatedAtAfter(Instant date);
}
```

---

## 2. RFC 7807 Standardized Error Responses (`ProblemDetail`)

```java
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Resource Not Found");
        problem.setProperty("timestamp", Instant.now());
        return problem;
    }
}
```
