# Git Workflows, Interactive Rebase, Worktrees & Reflog Recovery

## 1. Conventional Commits Standard
Format every commit message as `type(scope): concise imperative summary`:
- `feat`: New user-facing feature.
- `fix`: Bug fix.
- `refactor`: Behavior-preserving code restructuring.
- `test`: Adding or updating unit/integration tests.
- `chore`: Dependency, build, or config updates.

---

## 2. Linear History & Interactive Rebase
Squash noisy WIP/fixup commits before merging a feature branch:
```bash
# Interactively rebase the last 4 commits:
git rebase -i HEAD~4

# Or target a specific commit with autosquash:
git commit --fixup <commit-hash>
git rebase -i --autosquash <base-branch>
```

---

## 3. Disaster Recovery (`git reflog`) & Safe Aborts
Commits dropped via `git reset --hard` remain reachable in the reflog for at least 14 days:
```bash
# 1. Inspect HEAD movement history:
git reflog
# 3b4c5d6 HEAD@{0}: reset: moving to HEAD~1
# 9a8b7c6 HEAD@{1}: commit: feat(user): implement profile update

# 2. Restore the lost commit into a recovery branch:
git checkout -b recovery-branch 9a8b7c6
```
To abort a conflicted rebase or merge cleanly:
```bash
git rebase --abort
# or
git merge --abort
```

---

## 4. Isolated `git worktree` & Branch Completion Gate
- **Conflict & Secret Hygiene:** Inspect both sides of merge conflicts carefully and verify `.gitignore` excludes `.env`, credentials, and build artifacts before staging.
- **Worktree Workflow:**
  ```powershell
  # 1. Ensure .worktrees is ignored by git
  git check-ignore -q .worktrees

  # 2. Create an isolated worktree and feature branch
  git worktree add .worktrees/feat-x -b feat/x

  # 3. Verify baseline tests pass before starting work
  # 4. Run full test suite before merging/opening a PR (verification-before-completion)
  # 5. Remove worktree cleanly when finished
  git worktree remove .worktrees/feat-x
  ```
- Never run `git push --force` or `git reset --hard` unless explicitly requested by the user.
