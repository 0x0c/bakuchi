<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# Worktree and branch cleanup

Remove worktrees and branches whose work has already been merged to main.
This is a **mechanical, destructive-with-confirmation** skill — it never writes code.

## Steps

1. **List worktrees**

   ```bash
   git worktree list
   ```

2. **Identify merged branches**

   For each worktree, check if its branch has been merged to `origin/main`:

   ```bash
   git fetch origin
   git branch --merged origin/main
   ```

3. **Show the user what will be removed** — list each worktree path and branch name
   that is merged. Ask for confirmation before proceeding.

4. **Remove confirmed worktrees and branches**

   ```bash
   git worktree remove <path>
   git branch -d <branch>
   ```

   Use `-d` (not `-D`) so git refuses to delete unmerged branches.

5. **Prune** stale worktree metadata:

   ```bash
   git worktree prune
   ```

6. **Report** what was removed and what remains.

## What this skill does NOT do

- Remove unmerged worktrees or branches (always use `-d`, never `-D`)
- Force-delete anything without user confirmation
- Write code, run tests, or create PRs
