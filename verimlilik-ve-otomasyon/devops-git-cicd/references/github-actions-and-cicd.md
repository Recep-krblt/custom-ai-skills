# GitHub Actions & CI/CD Quality Gates

Synthesized from GitHub Actions best practices and CI/CD automation standards.

## 1. Shift-Left Quality Gate Order

Enforce automated gates before merge (`PR -> main`):
1. **Lint & Format** (fail fast on style/static errors)
2. **Type Check** (`tsc --noEmit`, `go vet ./...`, mypy)
3. **Unit & Integration Tests** (with service healthchecks e.g. PostgreSQL `pg_isready`, and explicit timeouts)
4. **Production Build** (`npm run build`, multi-stage `docker build`)
5. **Lockfile Dependency Audit** (`npm audit --audit-level=high` / native tool audit against committed lockfile)

Never skip failing gates or suppress rules to green a build.

## 2. Minimal Secure Workflow Structure

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
    paths-ignore: ['**.md', 'docs/**']

permissions:              # Least-privilege workflow default
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    runs-on: ubuntu-24.04 # Pin OS runner image
    timeout-minutes: 15   # Always bound runaway jobs
    steps:
      # Pin third-party actions to full commit SHAs resolved from the upstream repo
      - uses: actions/checkout@<pinned-commit-sha>  # verify current v4 SHA upstream
      - uses: actions/setup-node@<pinned-commit-sha>
        with:
          node-version: '24'
          cache: npm
      - run: npm ci
      - run: npm test
      - run: npm run build
```

## 3. Hardening Rules

- **Least-Privilege `permissions:`:** Declare workflow-level `contents: read`; grant `packages: write`, `pull-requests: write`, or `id-token: write` only on the specific job that needs it.
- **Full Commit SHA Pinning:** Pin third-party `uses:` actions to verified 40-char commit SHAs (never mutable `@v4` tags in privileged/release workflows), and inspect upstream changes before updating SHAs.
- **Prevent Expression / Shell Injection:** Never interpolate `${{ github.event.pull_request.title }}`, branch names, or workflow inputs directly inside `run:` scripts. Bind them to `env:` variables first and quote `"$VAR"` in shell or validate against strict allowlists.
- **`pull_request_target` Restriction:** Never check out or execute untrusted PR code/dependencies/artifacts inside a `pull_request_target` workflow with secrets or write permissions. Use standard read-only `pull_request` for tests and restrict `workflow_dispatch` / protected `environment:` gates with human reviewers for deployments.
- **Caching & Concurrency:** Scope dependency caches cleanly to lockfiles (`hashFiles('**/package-lock.json')` or `setup-node` built-in `cache`), set `timeout-minutes` on every job, and use `concurrency` to cancel obsolete PR runs (but set `cancel-in-progress: false` on production deploy jobs).
- **OIDC Over Long-Lived Secrets:** Prefer short-lived OIDC (`id-token: write`) scoped to exact repository, branch, and GitHub Environment instead of static cloud access keys.
