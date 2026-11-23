# Architecture & Deep Module Design

Standards for structuring modular codebases using deep modules, explicit seams, and minimal cognitive/test surface (distilled from Matt Pocock's MIT `codebase-design` principles).

## 1. Core Design Vocabulary
- **Module:** Any cohesive unit with an interface and implementation (function, class, package, or vertical slice). Avoid conflating with "service" or "component."
- **Interface:** Everything a caller must know to use a module safely—types/signatures, invariants, ordering constraints, error modes, performance bounds, and required configuration.
- **Implementation / Adapter:** *Implementation* is the internal logic body; *Adapter* is a concrete slot-filler implementing an interface at a **Seam** (a point where behavior can vary without editing callers).
- **Depth, Leverage & Locality:**
  - **Depth (Deep vs. Shallow):** High capability behind a small, simple interface (**Leverage** for callers) with logic, edge cases, and verification concentrated in one place (**Locality** for maintainers).
  - **Shallow Module (Anti-Pattern):** A thick, noisy interface wrapping a thin pass-through body—multiplies wiring, test stubs, and bugs across callers.

## 2. Four Structural Rules
1. **The Deletion Test:** Imagine deleting the module. If complexity disappears cleanly, it was an unnecessary pass-through wrapper; if complexity spills into N callers, the module earns its keep.
2. **Real Seam vs. Hypothetical Seam:** One adapter implies a speculative abstraction (wait until concrete variation exists); two real adapters (e.g., Stripe + Sandbox fake, PostgreSQL + SQLite) justify a seam.
3. **The Interface Is the Test Surface:** Callers and tests cross the same seam. Avoid splitting private helper functions out solely for unit-test whiteboxing when real failures live in the integration across them.
4. **Accept Dependencies, Return Values:** Inject external I/O handles/clients at the seam instead of instantiating them inline (`processOrder(order, gateway)`), and prefer pure calculation results over in-place argument mutation (`calculateDiscount(cart) -> Discount`).

## 3. Architecture Audit Protocol
When reviewing or refactoring a multi-file subsystem:
1. Check `GLOSSARY.md`, `docs/adr/`, and `.repo-map.md` (`token-and-context-ops`) before proposing structural shifts so accepted domain boundaries and ADRs are respected.
2. Prioritize hot-spot files (`git log --oneline -n 30`) where recent changes cause churn across many small files.
3. Flag specific friction with file/line evidence:
   - Understanding one domain flow requires jumping across 4+ shallow pass-through wrappers.
   - Domain validation, retries, or error mapping leaks across seams into controllers/UI callers.
   - Too many narrow boolean flags or multi-step caller ordering protocols exist where one cohesive interface method suffices.
4. Propose targeted deepening opportunities backed by the Deletion Test rather than broad speculative rewrites.
