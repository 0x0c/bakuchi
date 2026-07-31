<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# Roadmap status filter

Survey the roadmap by `Status`. This skill is **read-only**: it prints one table so you can pick
the items to open in full. It never authors, implements, or edits an item.

## What it does

Reading every file under `roadmaps/` is more than a session that needs one status wants to page
through. When you only need the items in one status, run the deterministic query instead:

```bash
python3 tools/roadmap_query.py --status "Proposal"
```

`STATUS` is one of the values below, matched case-insensitively:

- `Accepted` — the decision is made, implementation has not started
- `Accepted, in progress` — being built
- `Implemented` — shipped
- `Proposal` — open, not yet decided
- `Proposal (deferred)` — deliberately parked

An unknown status prints the valid values and exits non-zero, rather than an empty table.

The query is pure and offline. It reads each item's own metadata block under `roadmaps/`, with no
network access and no LLM. Pass `--topic` to narrow further, and `--json` when a script consumes
the result rather than a reader.

## Output

A Markdown table with four columns:

| Column | Meaning |
|---|---|
| `ID` | the item's `BK-NNNN`, or the `BK-XXXX` placeholder for an item whose number is not yet allocated |
| `Item` | the item's title |
| `Topic` | the item's Topic |
| `Path` | the relative path to the item's English `.md` file |

Rows are sorted by `Topic`, then `ID`.

## How to use it

1. Run the query for the status you care about.
2. Read the table to find the items relevant to the task.
3. **Open the file at the `Path`** of an item to get its full text. That column is exactly what to
   open next. For the Japanese mirror, swap the `.md` suffix for `-ja.md`.

Keep the survey narrow: pull only the status you need, then open only the items that matter. Doing
so is the whole point of the filter over reading every item wholesale.
