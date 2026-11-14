---
name: devops-git-cicd
description: Use when managing Git workflows (commits, rebase, worktrees, reflog), writing Dockerfiles or docker-compose.yml, or designing/securing GitHub Actions CI/CD workflows.
---

# DevOps, Git Workflows, Docker & GitHub Actions

Load the guide matching your infrastructure or version-control task:

| Scope | Reference Guide | Coverage |
| :--- | :--- | :--- |
| Conventional commits, rebase/squash, `worktree`, `reflog` | [references/git-workflows-and-recovery.md](references/git-workflows-and-recovery.md) | Clean history, pre-merge test gate |
| Multi-stage Dockerfiles, non-root containers, Compose | [references/docker-and-compose.md](references/docker-and-compose.md) | Image hardening, healthchecks, `.env` templates |
| GitHub Actions workflows, CI quality gates, hardening | [references/github-actions-and-cicd.md](references/github-actions-and-cicd.md) | Least-privilege `permissions:`, SHA pinning, `env:` safety |
