<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# Git sync + worktree preparation

Bring the local repo up to date and (optionally) set up an isolated worktree for a topic.
This is a **mechanical, command-only** skill — no design decisions, no code changes.

## Steps

1. **Fetch and rebase**

   ```bash
   git fetch origin
   git rebase origin/main
   ```

   If there are conflicts, report them and stop — don't resolve automatically.

2. **Worktree creation (when a topic is given)**

   Create the worktree at a sibling path, on a `claude/<topic>` branch cut from `origin/main`:

   ```bash
   git worktree add -b claude/<topic> ../bakuchi-<topic> origin/main
   ```

   Report the worktree path when done. If the user specifies a branch prefix (for example their
   username), use it in place of `claude/`.

3. **Report** the result: current branch, HEAD commit, worktree path (if created).

## What this skill does NOT do

- Implement features or write code
- Run `tools/check.sh` or tests
- Create PRs or commits
- Resolve merge conflicts (report and stop)

If the user asks to proceed with implementation after sync, tell them to start a new
session with the implement-bk workflow (or the appropriate skill).
