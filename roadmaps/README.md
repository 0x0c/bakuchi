**English** · [日本語](README-ja.md)

# bakuchi roadmap

Every design decision and every planned change lives here as a numbered **BK item**, in English and
Japanese. An item records what we decided, why, and what we ruled out — so that a decision can be
revisited on evidence rather than re-argued from memory.

> This page covers what an item *is* and how to add one. For the current state of any item, query
> its `Status` rather than reading a list here:
>
> ```bash
> python3 tools/roadmap_query.py --status "Proposal"
> ```

## Status vocabulary

| English | Japanese | Meaning |
|---|---|---|
| `**Accepted**` | `**可決**` | decided; implementation has not started |
| `**Accepted, in progress**` | `**可決・実装中**` | being built |
| `**Implemented**` | `**実装済み**` | shipped |
| `**Proposal**` | `**提案**` | open; not yet decided |
| `**Proposal (deferred)**` | `**提案（保留）**` | deliberately parked, with the conditions for reopening recorded |

`Accepted` is a deliberate addition to the vocabulary this format was borrowed from. bakuchi is a
design-stage repository, so a decision can be settled long before any code exists, and calling that
state `Proposal` would understate it while `Accepted, in progress` would overstate it.

`Proposal (deferred)` carries an obligation: an item parked without recorded trigger conditions is
an item nobody will ever revisit. See
[BK-0007](BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core.md) for the shape.

## Topics

`Platform strategy` · `Client SDK architecture` · `Config delivery` ·
`Assignment & determinism` · `Data pipeline` · `Statistics & analysis` · `Operations`

The list is a controlled vocabulary with a fixed Japanese counterpart for each value, enforced by
`tools/check_roadmap_format.py`. Adding a topic means editing that tool.

## Adding an item

**Never invent a BK number.** Author under the literal `BK-XXXX` placeholder and allocate at the
end, so two items started in parallel cannot collide.

```bash
# 1. Scaffold both language files
python3 tools/new_roadmap_item.py --slug <slug> --title "<title>" --title-ja "<タイトル>" --topic "<topic>"

# 2. Fill in every TBD, in both languages, to the same depth

# 3. Allocate the number (renames the directory and rewrites self-references)
python3 tools/new_roadmap_item.py --allocate

# 4. Verify
./tools/check.sh
```

**The one invariant: `BK-XXXX` must never appear outside the item's own directory.** The allocator
rewrites only that directory, so a placeholder written into a document, a specification, or a
comment elsewhere survives as a stale reference.

The [`ideation`](../.agent-workflows/ideation/workflow.md) workflow drives this procedure with an
agent; the commands above are the same either way.

## The file format

Each item is a directory holding two files:

```
roadmaps/BK-NNNN-<slug>/
  BK-NNNN-<slug>.md      English
  BK-NNNN-<slug>-ja.md   Japanese
```

Both files carry a bilingual header link, an `# BK-NNNN — <Title>` heading (an em dash, U+2014), a
metadata block fenced by `<!-- BK-METADATA -->` and `<!-- /BK-METADATA -->`, and six H2 sections in
a fixed order:

| English | Japanese |
|---|---|
| `## Introduction` | `## はじめに` |
| `## Motivation` | `## 動機` |
| `## Detailed design` | `## 詳細設計` |
| `## Alternatives considered` | `## 検討した代替案` |
| `## Progress` | `## 進捗` |
| `## References` | `## 参考` |

All six are mandatory. A section with nothing to say yet carries `TBD` rather than being omitted.
Anything else the item needs goes under an H3 inside one of the six.

**The fence around the metadata is load-bearing.** It lets the parser read exactly those rows and
never a same-shaped table elsewhere in the body. Metadata fields appear in this order:

| Order | English | Japanese | Required |
|---|---|---|---|
| 1 | `Proposal` | `提案` | always |
| 2 | `Author` | `提案者` | always |
| 3 | `Status` | `状態` | always |
| 4 | `Tracking issue` | `トラッキング Issue` | optional |
| 5 | `Implementing PR` | `実装 PR` | once shipped |
| 6 | `Topic` | `トピック` | always |
| 7 | `Related` | `関連` | optional |
| 8 | `Superseded by` | `後継` | optional |

## Both languages, to the same depth

The Japanese file is not a summary of the English one, and neither is a translation artifact of the
other. A reader of either language gets the whole argument. When drafting, read
[`document-writing`](../.agent-workflows/document-writing/workflow.md) together with the layer for
the language you are writing — those norms shape the draft rather than proofread it afterward.

## What is checked, and what is not

`tools/check_roadmap_format.py` gates the shape: the header link, the H1 form, the metadata fence
and field order, the status vocabulary, cross-language status and topic agreement, and the six
section headings. textlint gates the typography. **Neither judges the argument** — whether the item
leads with its contribution, whether the alternatives are treated fairly, whether a deferral records
its trigger conditions. That judgment is a review-time expectation, checked by people.

## Provenance

This format follows the convention of the [Bajutsu](https://github.com/bajutsu-e2e/bajutsu)
project, used under the Apache License 2.0. See
[`.agent-workflows/NOTICE`](../.agent-workflows/NOTICE) for the attribution.

## Unsorted ideas

> Add unformed thoughts here, then promote them to a numbered item once the scope is clear.

- **Bring the Japanese `docs/` under the prose norm.** The English documents were written under the
  norm and `tools/check.sh` lints them, but their Japanese counterparts predate it and do not conform
  yet, so the gate skips every `docs/**/*-ja.md`. Converting them is mechanical but large; scope it
  before numbering it.
