# Brainstorming Ideas Into Designs

Turn ambiguous ideas into validated, minimal designs **before** touching implementation files.

**Hard Gate:**
Do NOT write application code, scaffold files, or run destructive commands until you understand the existing codebase, clarify ambiguous requirements with the user, and align on an approach.

## Checklist

1. **Explore context first:**
   - Read `.repo-map.md` (or run `token-and-context-ops` (`references/repo-map-guide.md`) first) and check key config/manifest files (`package.json`, `pyproject.toml`, `GEMINI.md`, recent `git log -n 5`) to learn existing stack, conventions, and helpers.
2. **Assess clarity & decompose:**
   - If requirements have unstated constraints, tradeoffs, or multiple valid interpretations, ask focused questions **one concern at a time** (use `ask_question` with crisp options and a `(Recommended)` default when choices are bounded; use plain text for open-ended questions).
   - If the request bundles multiple independent subsystems, help the user scope MVP first before designing everything at once.
3. **Propose 2–3 concrete approaches:**
   - Compare each option briefly (complexity, reuse of existing code, tradeoffs) and state your **recommended** option clearly.
   - Apply **YAGNI** ruthlessly: cut speculative abstractions, unnecessary config layers, and features nobody asked for.
4. **Present the design cleanly:**
   - Break larger designs into short sections (Architecture/Data Flow, Components & File Boundaries, Error Handling, Testing Strategy) proportional to task complexity — a small feature needs 1–2 concise sections, not a 10-page doc.
   - Optionally validate design coherence using a fresh `research` subagent guided by [builder-check-prompt.md](builder-check-prompt.md) (adapted for reviewer/alignment inspection) when stakes are high.
5. **Save or hand off to implementation planning:**
   - Only persist a spec markdown doc if the user wants a recorded spec (write inside workspace `docs/specs/` or conversation artifacts if requested) — avoid creating unwanted clutter files for small tasks.
   - Once the user approves the design, transition cleanly to `workflow-planning-execution` (`references/writing-plans-and-breakdown.md`) (for multi-step/multi-file builds) or direct implementation for small single-file tasks.

## Antigravity Alignment Rules

- Respect existing repo patterns and helpers (`code_quality` guideline): prefer extending existing abstractions over inventing parallel frameworks.
- Keep questions short and technical; do not interrogate users with 6 unrelated questions in one block when 1–2 targeted questions clarify everything.
- When `workflow-planning-execution` (`references/brainstorming.md`) finishes on a clear, small task ("rename button", "fix typo", "add this exact CLI flag"), do not force bureaucracy — confirm briefly if ambiguous, or move straight to execution.
