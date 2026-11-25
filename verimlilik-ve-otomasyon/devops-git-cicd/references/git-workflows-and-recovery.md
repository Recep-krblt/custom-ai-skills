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
- **Worktree Setup:**
  ```powershell
  git check-ignore -q .worktrees
  git worktree add .worktrees/feat-x -b feat/x
  ```
- **Branch & Worktree Completion Protocol (`finishing-a-development-branch`):**
  1. **Verify Tests First:** Run the full project test suite; stop immediately if any test fails (never offer merge or PR over red tests).
  2. **Detect Context & Base Branch:** Check `git rev-parse --git-dir` vs `--git-common-dir` (normal repo vs named worktree vs detached HEAD) and confirm the target base branch with the user before merging.
  3. **Present Completion Choices:**
     - *Normal repo / named worktree:* `1. Merge back to <base> locally`, `2. Push & open Pull Request`, `3. Keep branch as-is`. (Detached HEAD: omit local merge, offer PR from new branch or keep as-is.)
     - Never discard branches/worktrees unprompted unless explicitly requested.
  4. **Merge & Post-Merge Proof Gate:** On local merge, switch to main repo root, run `git merge <feature-branch>`, and **re-run the full test suite on the merged base branch** before calling `git worktree remove` or `git branch -d`.
- Never run `git push --force` or `git reset --hard` unless explicitly requested by the user.
