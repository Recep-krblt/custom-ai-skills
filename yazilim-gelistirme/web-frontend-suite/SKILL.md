---
name: web-frontend-suite
description: Use when building or styling web UIs (React, Next.js, Astro, Tailwind CSS, HTML/CSS), optimizing Core Web Vitals, designing distinctive visual interfaces, or running Playwright browser tests.
---

# Web Frontend, Astro, Visual Design & Browser Testing

Load only the reference matching your frontend layer:

| Scope / Task | Reference / Asset | Notes |
| :--- | :--- | :--- |
| React, Next.js App Router, Tailwind, Core Web Vitals, Server Actions security | [references/react-nextjs-and-web-vitals.md](references/react-nextjs-and-web-vitals.md) | RSC boundaries, CLS/LCP, Zod gates |
| Astro SSG/SSR, `.astro` Islands Architecture, Content Collections | [references/astro-framework.md](references/astro-framework.md) | Zero-JS default + selective `client:*` |
| Typography, palette, motion & anti-template visual direction | [references/frontend-design-aesthetics.md](references/frontend-design-aesthetics.md) | 2-pass brief-driven design plan |
| Automated Playwright testing on local servers (vs `browser` / DevTools) | [references/playwright-webapp-testing.md](references/playwright-webapp-testing.md) | Helper: [scripts/with_server.py](scripts/with_server.py) & `examples/` |

> **Role Boundary:** For admin dashboards or existing-UI overhauls, defer aesthetics to `reference-design-contract` / workspace `impeccable` (`Operate` mode) rather than landing-page styling; pair Playwright flows with `chrome-devtools-plugin` (`a11y-debugging` / LCP) for live DOM audits.
