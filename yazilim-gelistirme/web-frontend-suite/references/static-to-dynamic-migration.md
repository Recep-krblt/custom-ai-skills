# Static-to-Dynamic Site & CMS Migration Guide

Methodology for converting hardcoded static websites (HTML/CSS/JS, Astro, React, Go/Jinja templates) into maintainable, schema-driven dynamic sites and CMS backends without breaking links, layouts, or security boundaries.

## Core Principles

1. **Audit Before Extracting:** Inventory every hardcoded string, object array, local asset path, `.html` route, and fixed-count layout assumption before designing database tables or APIs. Do not migrate unused legacy sections.
2. **Bind Logic to Slugs & IDs, Never Labels:** Conditionals and queries must reference stable `slug`, `type`, or `option_id` keys—never localized display strings (`"Featured"`, `"Lead"`), so editorial text edits cannot break behavior.
3. **Idempotent Seeding & Deterministic Asset Maps:** Every importer/migration script must be safe to re-run (`ON CONFLICT (slug) DO UPDATE`, content-hash asset IDs) with an explicit `source_path -> media_id/url` map.
4. **Fail-Safe Dynamic Rendering:** Escape editor/CMS fields by default and design explicit fallbacks for empty arrays, missing optional images, and unexpected long strings.
5. **URL & SEO Continuity:** Preserve every indexed path with dynamic routes or single-hop `301`/`308` redirects (`slug` history + edge/router redirects) and verify metadata parity (`<title>`, `<meta description>`, canonical, JSON-LD).

---

## Five-Phase Extraction Workflow

### Phase 1: Hardcoded Content & Dependency Audit
Run the bundled scanner across frontend templates/components first:
```powershell
python "<SKILLS_DIR>/web-frontend-suite/scripts/audit_hardcoded.py" <target-dir>
```
Classify all discovered findings into four buckets:
- **Copy & Structured Collections:** Hero text, navigation links, footers, card arrays (`const cards = [...]`), FAQ/team lists, contact emails/phones, `<meta>` tags.
- **Asset & Route Coupling:** Relative images/fonts (`/assets/...`, `./images/...`), CSS `url(...)`, hardcoded `http://localhost:...`, internal `.html` file links.
- **Structural Lock-In:** Fixed `items[0..2]` indexing, duplicated markup instead of loops, rigid pixel heights clipping longer CMS text.
- **Fragile Label Conditionals:** Display text used as business-rule discriminators.

### Phase 2: Content Model & Option-Pool Design (`backend-and-sql`)
- Separate **reusable layout shells** (header, footer, theme tokens) from **section content payloads**.
- Model structured repeating blocks with explicit schema contracts (normalized PostgreSQL tables or versioned/validated `JSONB` + `CHECK` constraints and indexed `slug`s—never untyped "blob of everything").
- Externalize dropdown choices, badges, and categories into option pools / lookup tables keyed by immutable `slug`s.
- Keep default seed data in isolated idempotent seed files (`presets/` or `seed/`), cleanly decoupled from renderer code.

### Phase 3: Idempotent Media, ID & Route Rewriting
1. **Extract & Hash Media First:** Upload/register local assets into managed media storage, storing a `source_relative_path -> media_id / resolved_url` lookup table before transforming templates.
2. **Rewrite Relative Paths for Nested Routes:** Relative `./assets/img.png` works on `/about.html` but breaks on `/blog/post-slug`; resolve all asset URLs from root/CDN or injected media helpers.
3. **Preserve Routes & Redirects:** Map legacy `.html` paths to clean dynamic routes (`old_path -> target_route`) with single-hop `301`/`308` redirects (never chain redirects) and preserve `alt` text and dimensions.
4. **Handle Circular References in Two Passes:** Insert base entities/media first, then link foreign keys and cross-page references in pass two.

### Phase 4: Template Extraction & Dynamic Security Gate (`cyber-security-analyst`)
- **Deduplicate Shared Shells:** Lift repeated `<head>`, nav, footer, and script/style links into base layouts/partials driven by site-wide settings (`siteName`, `navItems`, `socialLinks`).
- **XSS / Template Injection Gate:** Never render CMS/database strings via raw unescaped HTML sinks (`dangerouslySetInnerHTML`, `.innerHTML`, Go `template.HTML`, Jinja `|safe`, Astro `set:html`) unless explicitly required for rich text AND passed through a strict allowlist HTML sanitizer (`bluemonday`, `DOMPurify`).
- **Resilient Layout Bounds:** Guard every dynamic loop against `0` items (hide section or render neutral empty state), guard long titles with `min-w-0` + `line-clamp-*`/wrapping, and verify external links keep `rel="noopener noreferrer"`.

### Phase 5: Parity & Residual Hardcoding Verification
Before marking a static-to-dynamic migration complete:
- Re-run `audit_hardcoded.py` on refactored components/templates to confirm zero unintended static `.html` links, `localhost` leaks, or raw-HTML XSS sinks remain.
- Compare source vs. rendered output (`playwright-webapp-testing.md` or `chrome-devtools-plugin`):
  - Zero `404` requests on images, fonts, CSS, and internal links (including nested dynamic routes).
  - Preserved `<title>`, `<meta description>`, canonical URLs, and OpenGraph tags.
  - Responsive layout parity across desktop and mobile viewports using real varied-length CMS fixture data (short, empty, and extra-long inputs).

---

## Common Migration Pitfalls

| Pitfall | Failure Mode | Required Fix |
| :--- | :--- | :--- |
| Relative `./img/...` inside dynamic template | Works on `/`, 404 on `/posts/hello` | Rewrite to resolved root/media-service URLs via asset map |
| Raw DB HTML injected unescaped | Stored XSS from admin/CMS input | Escape by default; allowlist-sanitize only rich-text fields |
| Fixed card indexing (`cards[0..2]`) | Runtime panic/crash when CMS has 1 or 5 items | Render dynamically over slice/array with empty-state guard |
| Matching UI text (`if role == "Admin"`) | Translating or renaming label breaks logic | Key rules on immutable `slug` / enum code |
| Non-idempotent import script | Re-running seed duplicates rows/images | Key records on unique `slug` + hash-dedup media + `UPSERT` |
