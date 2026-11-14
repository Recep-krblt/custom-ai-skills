# React, Next.js & Core Web Vitals Architecture

Standards for Server/Client component boundaries, state colocation, Core Web Vitals optimization, and UI resilience.

## 1. Server vs Client Component Boundaries (RSC)
- **Server-First Default:** Keep Next.js App Router components as React Server Components (RSC) by default.
- **Leaf-Only `'use client'`:** Push `'use client'` down to the smallest interactive leaf component requiring state, effects, or browser event listeners; never mark whole page layouts as client components.
- **Eliminate Request Waterfalls:** Fetch independent data in parallel (`Promise.all`) inside RSCs; avoid chained `useEffect` fetches on the client.
- **Server Actions / API Security:** Treat every Server Action and route handler as a public HTTP endpoint—verify authentication, resource authorization, and Zod input schemas inside each handler.

## 2. Re-Render Prevention & State Colocation
- **Push State Down:** Isolate rapidly changing input state into dedicated child components so large parent tables/trees do not re-render.
- **Derived State:** Compute derived values inline during render (or via `useMemo` if expensive); never mirror props/state into redundant `useState` + `useEffect` sync loops.
- **State Libraries:** Use `TanStack Query` for server cache state and lightweight `Zustand` stores for global client state; ban `any` types across all props and API payloads.
- **Async UI States:** Always implement **Skeleton/Loading**, **Error Boundary**, and **Empty State** views alongside mobile-first breakpoints (`sm:`, `md:`, `lg:`).

## 3. Core Web Vitals, A11y & Verification Gate
- **CLS (Cumulative Layout Shift):** Always set explicit `width` and `height` (or `aspect-ratio`) on images/videos and match skeleton dimensions to loaded content.
- **LCP (Largest Contentful Paint) `< 2.5s`:** Preload hero media and critical fonts (`<link rel="preload">`); serve hashed static assets with `Cache-Control: public, max-age=31536000, immutable`.
- **INP (Interaction to Next Paint) `< 50ms`:** Offload heavy click/keyboard computations via `useTransition` or Web Workers.
- **Accessibility (A11y):** Enforce semantic landmarks (`main`, `nav`, `section`, `button`), visible keyboard focus (`focus-visible`), and explicit `<label>` / `aria-label` bindings.
- **Verification Gate:** Run `npm run build` and verify live browser rendering with zero console/network errors (`references/playwright-webapp-testing.md` & `quality-testing-review` (`references/verification-before-completion.md`)).
