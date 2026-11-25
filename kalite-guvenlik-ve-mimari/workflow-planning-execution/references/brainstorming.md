# Brainstorming Ideas Into Designs

Turn ambiguous ideas into validated, minimal designs **before** touching implementation files.

**Hard Gate:**
Do NOT write application code, scaffold files, or run build-out scripts until you understand the existing codebase, clarify ambiguous requirements with the user, and align on an approach.

## Checklist

1. **Recon existing code first:**
   - Read `.repo-map.md` (`token-and-context-ops`), key manifests (`package.json`, `pyproject.toml`, `GEMINI.md`), and recent `git log -n 5` before asking questions — never ask what the codebase or user prompt already answers.
2. **Why first & zero-filler questions (`v7.0.2` discipline):**
   - Ask a question **only** when the answer changes what gets built and nothing in context already settles it. Never ask about process mechanics (where docs live, whether to read another file); decide and state it.
   - If the user has not stated **why** they want the feature/system, ask one open question in plain language with **no predefined options** so you don't bias their goal.
   - Once intent is clear and a decision has concrete trade-offs, present 2–3 focused approaches (or `ask_question`) with pros/cons and mark your `(Recommended)` pick.
3. **State defaults out loud & offer fast opt-out:**
   - Any platform, language, library, or UX default you fill in must be stated explicitly as **your proposal** so the user can override it before build.
   - Apply **YAGNI** ruthlessly: cut speculative config layers, extra wrappers, and unrequested features.
   - If the prompt is already concrete with one obvious implementation path (e.g., `"rename button"`, `"add this CLI flag"`), summarize the concise short design + proposed defaults in one block with an opt-out (*"Or say 'just build it' and I'll proceed"*) instead of forcing multi-round interrogation.
4. **Present proportional design & optionally cross-check:**
   - Match length to scope (1–2 tight blocks for small changes; short Architecture/Flow, Seams/Files, Error Handling, Testing sections for larger builds).
   - For high-stakes multi-module projects, optionally run a fresh `research` subagent with [builder-check-prompt.md](builder-check-prompt.md) before finalizing.
5. **Save only when helpful & transition to planning:**
   - Avoid writing clutter design docs for trivial tasks; persist to `docs/specs/` (or conversation artifacts) only when the design warrants a durable record.
   - Once approved, hand off to `workflow-planning-execution` (`references/writing-plans-and-breakdown.md`) or direct execution for single-file edits.
