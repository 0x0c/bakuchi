<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# propose-and-build

Author a roadmap (BK) item **and** its implementation together, then land both in a **single pull
request**. You are the author and the implementer; the deterministic gate (`tools/check.sh`) is the
judge, never an LLM.

This skill composes the other two rather than restating them:

- [`ideation`](../ideation/workflow.md) authors a proposal and stops at the roadmap files.
- [`implement-bk`](../implement-bk/workflow.md) ships an already-numbered item from its ID.
- **`propose-and-build`** does both, in one pull request, for a small item the author is ready to
  build now.

## When to use it, and when not to

Use it when every one of the following holds:

- The design is settled. The discussion produced one obvious shape, not a set of options.
- The change is small enough to review as one pull request alongside its proposal.
- No prime directive is in tension, so the proposal needs no adjudication before building.

Otherwise run the serial path. Splitting the proposal from the implementation is what gives a
reviewer the chance to reject the design before anyone has written the code, and that separation is
worth the extra round trip whenever the design is genuinely open.

## How the ID arrives

Author the item under the literal `BK-XXXX` placeholder, exactly as `ideation` describes, and
allocate the real number at the end:

```bash
python3 tools/new_roadmap_item.py --slug <slug> --title "<title>" --topic "<topic>"
# ... author the item, build it, verify ...
python3 tools/new_roadmap_item.py --allocate
```

The allocator scans `roadmaps/` for the highest allocated number, renames the placeholder
directory, and rewrites every `BK-XXXX` self-reference inside the item's own two files.

**The one invariant: `BK-XXXX` must never appear outside the item's own directory.** The allocator
rewrites only `roadmaps/BK-XXXX-<slug>/`, so a placeholder written into code, a comment, a
specification, or a document elsewhere would survive as a stale reference. When the implementation
needs to name the item, allocate first, then reference the real number.

## Workflow

1. **Author the item** per [`ideation`](../ideation/workflow.md) steps 1 through 4, on a branch
   created from `origin/main`. Fill every section; a `TBD` that the same pull request implements is
   a contradiction.
2. **Implement it** per [`implement-bk`](../implement-bk/workflow.md) steps 4 and 5, against the
   *Detailed design* you just wrote. When building reveals the design was wrong, fix the item's
   prose in the same commit rather than letting the two drift apart. That correction is the main
   benefit of doing both at once.
3. **Allocate the ID**, then set `Status` to `**Implemented**` / `**実装済み**` in both files and
   fill the *Progress* section.
4. **Verify** with `./tools/check.sh`, and keep fixing until the gate is clean.
5. **Open the pull request** with a plain scoped title. Unlike an `implement-bk` pull request, this
   one carries **no** `[BK-NNNN]` prefix, because the number did not exist when the branch started.
   The body links the item, states what shipped, and names what the gate verified.

## What this skill does NOT do

- Land a design that is still genuinely open. Use the serial path instead.
- Invent a BK number by hand.
- Leave a `BK-XXXX` placeholder anywhere outside the item's own directory.
