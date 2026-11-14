# Multi-Stage Dockerfiles & Compose Isolation

Standards for minimal production container images, non-root execution, isolated Compose networks, and cached CI/CD pipelines.

## 1. Core Principles
- **Multi-Stage Builds:** Never ship compilers or `devDependencies` in production images.
- **Non-Root Execution:** Always create and switch to an unprivileged system user (`USER appuser`).
- **Compose Network Isolation:** Isolate databases, Redis, and internal services on dedicated `docker-compose` networks with `.env` templates.
- **Verification Gate:** Validate `Dockerfile` and Compose changes by running `docker compose config` / `docker build` and verifying container healthchecks (`quality-testing-review` (`references/verification-before-completion.md`)).

---

## 2. Hardened Multi-Stage `Dockerfile` Template

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --production

# Stage 2: Production Runtime (Minimal & Non-Root)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist

USER appuser
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

---

## 3. GitHub Actions CI Quality Gate with Dependency Caching

```yaml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Type Check & Lint
        run: |
          npm run typecheck
          npm run lint

      - name: Run Tests with Coverage
        run: npm run test:coverage
```
