# Agent workflows

Host-agnostic instructions for the agents that work on this repository. Each subdirectory holds one
`workflow.md`, the full procedure for one task, written so any agent host can follow it.

`.claude/skills/<name>/SKILL.md` holds the thin Claude Code adapter for each workflow: front matter
naming the skill, and one line pointing at the `workflow.md` here. Splitting the two keeps the
procedure in one place while letting each host describe it in whatever form that host expects.

## The workflows

| Workflow | What it does | Writes files? |
|---|---|---|
| [`document-writing`](document-writing/workflow.md) | The prose norm both languages share, plus the bundled textlint runtime | no |
| [`english-document-writing`](english-document-writing/workflow.md) | English mechanics, beneath the norm above | no |
| [`japanese-document-writing`](japanese-document-writing/workflow.md) | 日本語の文章規範。同じ傘の下の日本語レイヤー | no |
| [`ideation`](ideation/workflow.md) | Shapes an idea into a bilingual roadmap (BK) item, and stops there | `roadmaps/` only |
| [`implement-bk`](implement-bk/workflow.md) | Ships an already-numbered item end to end | yes |
| [`propose-and-build`](propose-and-build/workflow.md) | Authors an item and builds it in one pull request | yes |
| [`roadmap-filter`](roadmap-filter/workflow.md) | Lists roadmap items by `Status` | no |
| [`task-select`](task-select/workflow.md) | Recommends the next task from issues and the roadmap | no |
| [`git-sync`](git-sync/workflow.md) | Fetch, rebase, and optional worktree setup | no |
| [`pr-followup`](pr-followup/workflow.md) | Fixes CI failures and review comments on an open pull request | yes |
| [`cleanup`](cleanup/workflow.md) | Removes merged worktrees and branches, after confirmation | no |

## The roadmap triangle

Three workflows cover authoring and building, and they compose rather than overlap:

```
ideation ──────────── authors a proposal, never implements
   │
   ├── implement-bk ── ships an already-numbered item
   │
   └── propose-and-build ── does both, in one PR, for a small settled item
```

Reach for `propose-and-build` only when the design is settled. Splitting the proposal from the
implementation is what lets a reviewer reject a design before anyone writes the code.

## Verification

Two gates are mechanical, and both run from `tools/check.sh`:

```bash
./tools/check.sh
```

- **Shape** — `tools/check_roadmap_format.py` validates every roadmap item against the canonical
  skeleton, in both languages.
- **Determinism** — `tools/verify_vectors.py` checks the bucketing implementation against
  `spec/golden-vectors.json`.
- **Typography** — textlint, over the roadmap items and documentation.

`.github/workflows/check.yml` runs the same script on every pull request, with
`CHECK_REQUIRE_TEXTLINT=1` set so that a missing textlint install fails the run rather than
skipping quietly. A gate that reports green without having checked anything is worse than a red
one.

The prose norms themselves are a review-time expectation, checked by people. Judging clarity and
argument order needs semantic judgment that no deterministic check supplies.

## Provenance

These workflows are adapted from the [Bajutsu](https://github.com/bajutsu-e2e/bajutsu) project
under the Apache License 2.0. [`LICENSE`](LICENSE) carries the license text, and
[`NOTICE`](NOTICE) records the attribution and lists what was adapted versus taken unmodified.
