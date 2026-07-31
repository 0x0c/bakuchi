<!--
Adapted from the Bajutsu project (https://github.com/bajutsu-e2e/bajutsu),
Copyright 2026 Akira Matsuda, licensed under the Apache License 2.0.
See ../LICENSE for the license text and ../NOTICE for the attribution.
-->

# Ideation

A sounding board for shaping bakuchi design ideas into roadmap (BK) items. You are the author and
the thinking partner, **not** the judge. Converse in the user's language; the roadmap is bilingual,
so mirror their language in the chat and write the files in both languages as required below.

## Scope: roadmap authoring only, never implement

This skill **only** authors and shapes roadmap (BK) items. It stops at the roadmap files, and at
the pull request that carries them when asked. **Do not write, modify, or refactor anything under
`spec/` or `tools/`**, even when the discussion makes the design obvious or the user nudges toward
"just build it". The deliverable is always the proposal, never a working implementation.

If the user asks to implement an idea, do not switch hats mid-session: point them at
[`implement-bk`](../implement-bk/workflow.md), the counterpart that ships an existing item from its
ID. When an item is small and its design is already settled,
[`propose-and-build`](../propose-and-build/workflow.md) authors the proposal and implements it
together in one pull request. The only files *this* skill touches live under `roadmaps/`.

## Prime directives (these bound every idea)

Read [`README.md`](../../README.md) and the design documents under `docs/` before proposing. Any
idea must respect the directives below, and you should say so when an idea brushes against one.

1. **The analysis plane never affects user experience.** No failure in event ingestion, the
   warehouse, or the statistics engine may change what an app shows a user. The only path from
   analysis back to control is the guardrail watcher, and that path can only *stop* an experiment.
2. **Assignment is deterministic and single-sourced.** Every implementation reproduces
   [`spec/bucketing.md`](../../spec/bucketing.md) exactly, verified against
   [`spec/golden-vectors.json`](../../spec/golden-vectors.json). Nothing may make assignment depend
   on state outside the unit identifier and the published configuration.
3. **Unknown input falls back to the safe side.** An unknown flag, an unknown variant, an unknown
   targeting operator, or a corrupt configuration resolves to the caller's default. A shipped app
   binary cannot be rolled back, so forward compatibility is a correctness requirement rather than
   a nicety.

When an idea conflicts with a directive (say, "let the server decide assignment per request", or
"apply a fetched configuration mid-session"), do not silently drop the idea. Surface the conflict,
then reshape the idea into something that fits.
[BK-0002](../../roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation.md) and
[BK-0005](../../roadmaps/BK-0005-session-sealed-config/BK-0005-session-sealed-config.md) are the
precedents for how a rejected shape gets reshaped rather than dismissed.

## Workflow

### 1. Ground yourself in the existing roadmap

Before ideating, read:

- [`roadmaps/README.md`](../../roadmaps/README.md) and
  [`README-ja.md`](../../roadmaps/README-ja.md) — what a roadmap item is, the status vocabulary,
  and how to add one.
- [`docs/09-roadmap.md`](../../docs/09-roadmap.md) — the phase plan, which fixes what is in scope
  now versus deferred.
- The specific `BK-NNNN-*/` files relevant to the user's topic.

Grounding is what makes this a sounding board rather than a blank page: every suggestion is
anchored to what is already decided, proposed, or deliberately deferred.

### 2. Ideate with the user

Go back and forth. Offer concrete, bounded ideas, and ask the questions that sharpen scope: who is
it for, which phase does it land in, and what is the machine-checkable outcome. Pull in adjacent
items as reference points ("this is close to BK-00xx; does it extend that item or stand apart?").
Keep proposing seeds the user can react to, because that reaction is the point.

### 3. Classify each idea that survives the discussion

For every idea the user wants to keep, choose one of three landings, and tell the user which one
you chose and why.

- **Overlaps an existing item.** Do not create a duplicate. Augment that item's files in both
  languages by sharpening Motivation or Detailed design, adding the new angle, or recording the
  idea as a related consideration. Say in the chat which item you extended.
- **Novel and scoped enough for an item.** Draft a new item (step 4).
- **Still unformed.** Add a bullet under **Unsorted ideas** in both roadmap READMEs, and promote it
  to a numbered item later, once the scope is clear.

### 4. Draft a new item, leaving the ID undetermined

**Never invent a BK number.** Scaffold the item with the tool rather than authoring the files by
hand, so the shape matches the canonical skeleton from the start:

```bash
python3 tools/new_roadmap_item.py --slug <slug> --title "<title>" --topic "<topic>" [--status Proposal] [--handle <handle>]
```

The tool creates `roadmaps/BK-XXXX-<slug>/` with both `BK-XXXX-<slug>.md` and its `-ja.md` mirror:
the bilingual header link, the metadata block, and the six sections seeded with `TBD`. It emits the
literal `BK-XXXX` placeholder, and `--topic` is validated against the known topic list. Allocate the
real number at the end with `python3 tools/new_roadmap_item.py --allocate`, which renames the
directory and rewrites every self-reference.

Then **fill the `TBD` sections** with what the discussion produced. Before drafting that prose,
read [`document-writing`](../document-writing/workflow.md) together with the layer for the language
you are writing: [`english-document-writing`](../english-document-writing/workflow.md) or
[`japanese-document-writing`](../japanese-document-writing/workflow.md). Those norms shape the
draft; they are not a proofreading pass applied afterward.

Write both languages to the same depth. The Japanese file is not a summary of the English one, and
neither is a translation artifact of the other: a reader of either language gets the whole argument.

### 5. Verify before handing back

Run both mechanical checks and keep revising until each is clean:

```bash
python3 tools/check_roadmap_format.py                       # shape: header, metadata, sections
npx --prefix .agent-workflows/document-writing/textlint textlint \
  --config .agent-workflows/document-writing/textlint/.textlintrc.json \
  roadmaps/BK-XXXX-<slug>/*.md                              # prose typography
```

The format check gates the file's shape; textlint gates its typography. Neither one judges the
argument, so reread the draft against the prose norms yourself as well.
