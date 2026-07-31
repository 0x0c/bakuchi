<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# implement-bk

Ship an existing, already-numbered roadmap item end to end: the change itself, its verification,
the item's status update, and the pull request that carries them. You are the implementer; the
deterministic gate (`tools/check.sh`) is the judge, never an LLM.

Invoke it with an item ID: `implement-bk BK-0004`. When the item does not exist yet, use
[`ideation`](../ideation/workflow.md) to author the proposal first, or
[`propose-and-build`](../propose-and-build/workflow.md) when the item is small and its design is
already settled.

## Prime directives

The directives in [`ideation`](../ideation/workflow.md#prime-directives-these-bound-every-idea)
bound the implementation as much as the proposal. Restated for the implementer:

1. **The analysis plane never affects user experience.** Do not add a path where an ingestion,
   warehouse, or statistics failure changes what an app shows.
2. **Assignment is deterministic and single-sourced.** Any code that assigns a unit to a variant
   reproduces [`spec/bucketing.md`](../../spec/bucketing.md) and passes
   [`spec/golden-vectors.json`](../../spec/golden-vectors.json). A change that alters a golden
   vector is a breaking change to every live experiment, so it needs its own roadmap item.
3. **Unknown input falls back to the safe side.** Unknown flags, variants, operators, and corrupt
   configuration resolve to the caller's default.

When the item as written conflicts with a directive, stop and say so rather than implementing
around it. Amending the item is the correct move, and that belongs to `ideation`.

## Workflow

### 1. Read the item, both languages

Open `roadmaps/BK-NNNN-<slug>/BK-NNNN-<slug>.md` and its `-ja.md` mirror. The two files are written
to the same depth, so a detail present in one and missing from the other is a defect worth fixing
while you are here.

Read the *Detailed design* section as the specification, and *Alternatives considered* as the
record of what was already ruled out. Do not re-litigate a rejected alternative during
implementation; when the rejection turns out to be wrong, that is a new roadmap item.

### 2. Confirm scope before writing anything

State back, in one short list, what you are about to change and what you are deliberately leaving
alone. An item whose *Detailed design* still carries `TBD` in a section you would have to
implement is not ready: say which section, and hand it back to `ideation`.

### 3. Branch

```bash
git fetch origin
git checkout -B claude/<topic> origin/main
```

### 4. Implement against the specification

Work in the order the item's *Detailed design* lays out. Where the item names a machine-checkable
outcome, write that check first, watch it fail, then make it pass. A change to anything under
`spec/` requires the corresponding golden vectors to be regenerated **and** cross-verified in at
least two independent language implementations before it lands.

### 5. Verify

```bash
./tools/check.sh
```

Keep fixing and rerunning until the gate is clean. Never mark an item Implemented on a red gate,
and never loosen a check to make it pass: the check is the judge.

### 6. Update the item's status

Set `Status` to `**Implemented**` in the English file and `**実装済み**` in the Japanese one, then
add the `Implementing PR` row to both. Fill the *Progress* section with what actually shipped, and
say plainly when part of the item's design was deferred rather than delivered.

### 7. Open the pull request

Title the pull request `[BK-NNNN] <scoped summary>`. In the body, link the item, say what shipped,
and list what the gate verified. When the item's scope was reduced along the way, say which part
was cut and why, in the body rather than only in the roadmap file.

## What this skill does NOT do

- Author a new roadmap item, or renumber an existing one
- Change the bucketing specification without a roadmap item authorizing it
- Merge its own pull request
- Mark an item Implemented when the gate is red or the design was only partly delivered
