# Creating & Improving Antigravity Skills

Creating or upgrading a skill is test-driven process engineering: start from real agent failure modes, design crisp triggers, verify under pressure, and validate structure deterministically.

## Skill Storage Locations in Antigravity

- **Global skills (cross-project):** `C:\Users\<USERNAME>\.gemini\config\skills\<skill-name>\` (registered via `~/.gemini/config/skills.json`)
- **Workspace skills (repo-local):** `<workspace>\.agents\skills\<skill-name>\`

## Required Directory Layout

```text
<skill-name>/
├── SKILL.md            # Required: YAML frontmatter + core workflow (< 300 lines preferred)
├── references/         # Optional: heavy checklists, code templates, domain tables
├── scripts/            # Optional: deterministic CLI helpers (--help supported)
└── assets/             # Optional: templates, schemas, fonts, fixtures
```

Only create directories you actually populate — avoid empty scaffolding folders or redundant `README.md`/`CHANGELOG.md` files inside skill directories.

## Anatomy of a High-Signal `SKILL.md`

### 1. Frontmatter & Skill Discovery Optimization (SDO)

Antigravity loads **only `name` and `description`** into every prompt until a skill triggers.

```yaml
---
name: my-skill-name
description: Use when [specific symptoms, file types, or trigger conditions].
---
```

- **`name`:** Must exactly match the parent folder name (`[a-z0-9-]`, max 64 chars, no leading/trailing/double hyphens).
- **`description` (max 1024 chars, target <= 350 chars):**
  - **MUST state WHEN to use** (symptoms, error classes, file formats, user intent).
  - **NEVER summarize the skill's steps/workflow** inside `description`. Models shortcut and skip reading `SKILL.md` when the description already reveals the steps.
  - See [discovery-and-bulletproofing.md](discovery-and-bulletproofing.md) for SDO & anti-rationalization patterns.

### 2. Progressive Disclosure & Cross-Platform Discipline

- Keep core `SKILL.md` tight and scannable (decisions, gates, commands, anti-patterns); offload verbose examples and catalogs to `references/*.md` (one level deep, explicitly linked from `SKILL.md` with relative paths).
- **Windows / PowerShell readiness:** Avoid hardcoded POSIX `/tmp/` or `/mnt/` paths in examples or scripts (`tempfile.gettempdir()` in Python, `$env:TEMP` in PowerShell); force UTF-8 output (`reconfigure(encoding="utf-8", errors="replace")`) when scripts print non-ASCII text.
- **Keep global budget lean:** Every installed skill taxes system context on every turn. Prefer strengthening existing domain skills or bundling focused references over installing dozens of thin, overlapping wrappers.

## TDD Workflow for Authoring or Upgrading Skills

1. **RED (Baseline):** Identify concrete failures — either run a prompt/scenario with `invoke_subagent` without the skill or inspect gaps/rationalizations in an existing skill.
2. **GREEN (Minimal Skill):** Draft `SKILL.md` addressing those exact failure modes and closing loopholes with clear gates and verification steps.
3. **REFACTOR (Bulletproof & Trim):** Check for workflow spoilers in `description`, prune fluff, extract heavy templates into `references/`, and test trigger/compliance with a fresh `invoke_subagent`.

## Mandatory Validation Step (`quality-testing-review` (`references/verification-before-completion.md`))

After creating or editing any skill, run the deterministic validator via `run_command`:

```powershell
python C:\Users\<USERNAME>\.gemini\config\skills\skill-and-mcp-tools\scripts\validate_skills.py C:\Users\<USERNAME>\.gemini\config\skills
```

To validate a single skill or workspace `.agents\skills` folder:

```powershell
python C:\Users\<USERNAME>\.gemini\config\skills\skill-and-mcp-tools\scripts\validate_skills.py <path-to-skills-root>
```

Never report a skill change complete until `validate_skills.py` exits `0` with `0` errors and any bundled `--help`/smoke tests pass.
