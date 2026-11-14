# Codebase Skeleton & Repository Map (repo-map)

This skill provides deterministic, token-efficient codebase navigation for multi-module architectures, web portals, and large codebases (e.g., <PROJECT_NAME>, enterprise apps). It stops agents from burning context windows on blind file exploration (`read_file`, wide `grep`).

## Activation Criteria
- **Trigger When:** 
  - Working on multi-file repositories or unfamiliar codebases.
  - User asks to "scan project", "analyze architecture", "find where X is defined", or troubleshoot across modules.
  - Prior to reading multiple files or locating symbols (controllers, models, routes, templates, components).
- **Do NOT Trigger When:** Working on isolated single-file scripts or when the exact file path and line number are already explicitly provided.

---

## Standard Protocol: "Map-First" Navigation

The agent MUST follow this 4-tier navigation sequence without deviation:

### Tier 1: Check or Synchronize the Map
Check if `.repo-map.md` exists in the project root. If missing or stale (files modified/added), execute the generator script:
```powershell
python "C:\Users\<USERNAME>\.gemini\config\skills\token-and-context-ops\scripts\generate_repo_map.py" .
```
For instant symbol lookup (supports `|` OR queries) without parsing the entire markdown file:
```powershell
python "C:\Users\<USERNAME>\.gemini\config\skills\token-and-context-ops\scripts\generate_repo_map.py" . --find "SymbolA|SymbolB|POST /admin"
```

### Tier 2: Zero Blind Reads
NEVER read whole files or run wide directory searches to guess where functions, classes, or HTML elements live. Always inspect `.repo-map.md` first to identify exact file paths and symbol line ranges (`Lxx` or `Lxx-Lyy`).

### Tier 3: Surgical Inspection
Once the target symbol is identified in the map, use `read_file` with exact `StartLine` and `EndLine` parameters matching the `(Lxx-Lyy)` range to pull only the relevant block into context.

### Tier 4: Fallback & Non-Abandonment Guarantee
If the problem is a runtime bug, subtle logic flaw, CSS collision, or side-effect that cannot be pinpointed solely from method signatures in the map:
- **NEVER dismiss the issue** or conclude that "no problem exists".
- Escalate immediately to targeted token-filtered searches (`Select-String` / targeted regex on specific error keywords) or `quality-testing-review` (`references/systematic-debugging.md`).
- Read the suspect file in full or inspect runtime logs/tests until the root cause is resolved (`quality-testing-review` (`references/verification-before-completion.md`)).

> Script options: pass `--check` to verify freshness, `--max-symbols 0` to lift per-file markdown truncation, or `--find "A|B|C"` for lossless multi-query OR search across all indexed symbols (Go structs/interfaces/receivers/routes, SQL `CREATE`/`ALTER TABLE`, `.html` inline `<script>` JS, `.astro`/`.svelte`/`.vue`, `.rs`, `.ps1`, `.md`).
