**English** · [日本語](BK-0001-build-vs-buy-ja.md)

# BK-0001 — Build or buy the experimentation platform

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0001](BK-0001-build-vs-buy.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Accepted** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0001%22) |
| Topic | Platform strategy |
<!-- /BK-METADATA -->

## Introduction

An A/B testing platform is a mature product category with several credible vendors and one strong
open-source option, so building one deserves a justification rather than an assumption. This item
fixes the conditions under which bakuchi is built in-house, and names what to adopt instead when
those conditions do not hold. Every other roadmap item assumes the answer here is "build"; when it
is not, none of them apply.

The decision is a gate rather than a preference. It is evaluated once, during the two-week Phase 0
described in [`docs/09-roadmap.md`](../../docs/09-roadmap.md), and a conclusion of "do not build"
is a successful outcome of that phase.

## Motivation

The cost of an experimentation platform is not the cost of writing it. A platform that assigns
users to variants and reports which variant won produces numbers that a company then acts on, and
wrong numbers are worse than no numbers, because a team acts on them with confidence. Keeping the
numbers right means continuously verifying the statistics, monitoring data quality, and advising on
experiment design. That work does not end when the code ships.

Skipping the build-or-buy question tends to produce one specific failure: a platform that runs, but
whose results nobody trusts. Once a team has been burned by one experiment whose conclusion was
later found to be an artifact of the pipeline, the platform stops being consulted, and the
investment is written off. Naming the staffing condition up front is how we avoid that outcome.

The commercial alternatives are priced per monthly active user, so the comparison shifts with
scale. Below roughly a million monthly active users, a vendor costs less than the engineers it
would take to replace it; well above that, the ordering reverses. Any decision that ignores the
crossover point is arguing from preference rather than from cost.

## Detailed design

### The conditions

Build in-house only when **every** condition below holds. When any one fails, self-host
[GrowthBook](https://www.growthbook.io/) instead.

1. **Scale.** At least one million monthly active users, so that per-user vendor pricing exceeds
   the cost of the engineers who would replace it.
2. **Usage.** At least fifty experiments per year, so the investment in the platform is amortized
   over enough decisions to matter.
3. **Staffing.** At least two engineers who own the platform after it ships. Statistical
   verification, data-quality monitoring, and experiment-design consulting are continuing work, not
   a launch task.
4. **Metric integration.** Experiments need metric definitions that live in the company's own data
   warehouse and cannot be reproduced inside a vendor's model.
5. **Mobile requirements.** A proof of concept has shown that the mobile-specific requirements —
   the configuration compiled into the app binary, layer-based mutual exclusion, and offline
   evaluation — are not satisfied by an off-the-shelf product.

Condition 3 is the one most often skipped, and it is the one that decides whether the platform is
still trusted a year after launch.

### The comparison

| Option | Cost | Strengths | Weaknesses |
|---|---|---|---|
| Firebase A/B Testing / Remote Config | free to low | mature mobile SDKs, adopted in days | Bayesian-only statistics, no variance reduction, no sample-ratio diagnostics, no layer exclusion, cannot use warehouse metrics |
| GrowthBook, self-hosted | infrastructure only | reads the company's own warehouse, sound statistics including variance reduction and sequential testing, multi-language SDKs | mobile SDKs shallower than a purpose-built one, operated in-house |
| LaunchDarkly / Optimizely / Statsig | high, scales with monthly active users | complete product, vendor support | per-user pricing grows linearly with scale, data leaves the company, mobile-specific requirements are out of reach |
| Build in-house | four to six engineer-months, plus continuing operation | full control, integrates with existing systems, optimized for the mobile constraints | construction and operation cost; wrong statistics do more harm than no platform |

### The hybrid option

A middle path is easy to overlook and often the strongest: **deliver configuration with an existing
product, and analyze in-house.** Send exposure events into the company's own pipeline, and build
only the statistics layer. Doing so skips the most expensive component, the mobile SDK, while
keeping the most valuable one, correct statistics over the company's own metrics. Starting Phase 1
in that shape and building the SDK later, once configuration delivery proves to be the constraint,
is a defensible path rather than a compromise.

## Alternatives considered

- **Assume "build" and skip the evaluation.** Rejected because it hides the staffing condition,
  which is the condition that decides whether the platform survives its first year.
- **Adopt a commercial vendor unconditionally.** Rejected because per-user pricing grows linearly
  with scale while the in-house cost does not, so the comparison genuinely reverses above the
  crossover point. Ignoring the reversal is arguing from preference.
- **Decide later, after Phase 1 is underway.** Rejected because Phase 1 builds the SDK and the
  delivery path, which is exactly the work a vendor would replace. Deciding after that work is
  sunk means never really deciding.

## Progress

- [ ] Evaluate the five conditions during Phase 0.
- [ ] Confirm whether an existing data warehouse is available, which also settles
      [BK-0006](../BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md).
- [ ] Record the conclusion here, including the reasoning, whichever way it goes.

## References

- [`docs/09-roadmap.md`](../../docs/09-roadmap.md) — Phase 0, where this decision is made.
- [`docs/03-tech-selection.md`](../../docs/03-tech-selection.md) — the technology selection that
  assumes a "build" outcome.
- [BK-0006](../BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md) — the
  warehouse decision, settled in the same phase.
