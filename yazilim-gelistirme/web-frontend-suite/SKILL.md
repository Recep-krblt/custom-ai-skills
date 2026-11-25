---
name: web-frontend-suite
description: Use when building or styling web UIs (React, Next.js, Astro, Tailwind CSS, HTML/CSS), migrating static sites into dynamic CMS/SSR templates (extracting hardcoded text, arrays, assets, and links), optimizing Core Web Vitals, or running Playwright browser tests.
---

# Web Frontend, Astro, Static-to-Dynamic Migration & Testing

Load only the reference matching your frontend layer:

| Scope / Task | Reference / Asset | Notes |
| :--- | :--- | :--- |
| React, Next.js App Router, Tailwind, Core Web Vitals, Server Actions security | [references/react-nextjs-and-web-vitals.md](references/react-nextjs-and-web-vitals.md) | RSC boundaries, CLS/LCP, Zod gates |
| Astro SSG/SSR, `.astro` Islands Architecture, Content Collections | [references/astro-framework.md](references/astro-framework.md) | Zero-JS default + selective `client:*` |
| Static-to-dynamic / CMS extraction & hardcoded cleanup | [references/static-to-dynamic-migration.md](references/static-to-dynamic-migration.md) | Scanner: [scripts/audit_hardcoded.py](scripts/audit_hardcoded.py) |
| Typography, palette, motion & anti-template visual direction | [references/frontend-design-aesthetics.md](references/frontend-design-aesthetics.md) | 2-pass brief-driven design plan |
| Automated Playwright testing on local servers (vs `browser` / DevTools) | [references/playwright-webapp-testing.md](references/playwright-webapp-testing.md) | Helper: [scripts/with_server.py](scripts/with_server.py) & `examples/` |

> **Cross-Skill Contract:** Pair static-to-dynamic CMS migrations with `backend-and-sql` (typed schemas, option pools, idempotent upserts) and `cyber-security-analyst` (XSS/HTML sanitization); for UI overhauls defer aesthetic direction to `reference-design-contract` (`open-design-contracts`), and pair Playwright flows with `chrome-devtools-plugin` (`a11y-debugging` / LCP).
