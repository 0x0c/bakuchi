**English** · [日本語](BK-0007-revisit-kmp-shared-core-ja.md)

# BK-0007 — Revisit a shared Kotlin Multiplatform SDK core

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0007](BK-0007-revisit-kmp-shared-core.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal (deferred)** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0007%22) |
| Topic | Client SDK architecture |
| Related | [BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) |
<!-- /BK-METADATA -->

## Introduction

[BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) ships two native software development kits
(SDKs), one in Swift and one in Kotlin, and rejects a shared Kotlin Multiplatform core. That
rejection rests on the current scale of the SDK, not on the merits of the technology, so it can
stop being correct without anyone noticing.

This item exists to make the reversal observable. It records the conditions under which the
decision is reopened, so that reopening happens on evidence rather than on whoever is most tired of
writing every change twice.

## Motivation

A decision justified by scale needs a stated trigger, because scale changes silently. Without one,
two outcomes are both likely and both bad. The team keeps two implementations well past the point
where sharing would be cheaper, because reversing a written decision feels like relitigating it. Or
someone reverses it during an unrelated piece of work, on the strength of a single frustrating
afternoon, without the evidence that would justify the migration cost.

Writing the triggers down converts the question from a matter of preference into a matter of fact.

## Detailed design

### Trigger conditions

Reopen this decision when **any one** of the following holds. Each is chosen to be observable
rather than a matter of judgment.

1. **The SDK core exceeds 5,000 lines** on either platform, excluding tests and platform-specific
   input and output. The rejection in BK-0003 rests on the shareable surface being small; past this
   size, that premise no longer holds.
2. **Two or more defects are traced to a behavioral difference between the two implementations.**
   One such defect is a mistake; two is a pattern, and it is direct evidence that the specification
   plus golden vectors are not covering the surface they were assumed to cover.
3. **Targeting operators are added twice per quarter or more often,** and the duplicated work is
   observably slowing delivery. The cost of two implementations is proportional to the rate of
   change, so a sustained rise in that rate changes the arithmetic.

### What to evaluate on reopening

Reaching a trigger opens the question rather than settling it. The evaluation still has to weigh:

| Factor | What to measure |
|---|---|
| Binary size | actual growth of a release build with the shared core, not the published estimate |
| Startup time | whether `start()` still fits the 10 ms budget with the Kotlin/Native runtime |
| Swift ergonomics | how the generated surface reads at call sites, including suspend-function bridging |
| Migration cost | the work to move existing call sites, and the release risk of shipping it |
| Team agreement | whether the iOS team accepts the resulting binary growth |

The last row is a gate rather than a factor. An SDK the iOS team declines to adopt has no value,
which is the same argument that produced the original decision.

### What stays true either way

Whatever this item concludes, the golden vectors remain the guarantee of cross-language agreement.
Adopting a shared core would remove one *source* of divergence; it would not remove the need to
verify agreement, because the Go and Python implementations on the server side stay separate under
[BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md). Sharing the mobile core is a
narrowing of the problem, not a solution to it.

## Alternatives considered

- **Leave the reversal to a future judgment call, with no recorded triggers.** Rejected because it
  produces the two failure modes named under Motivation: reversing too late out of deference to a
  written decision, or too early on the strength of one frustrating afternoon.
- **Commit now to migrating at a fixed date.** Rejected because the cost of two implementations is
  proportional to the rate of change, which no date predicts. Migrating on a schedule risks paying
  the migration cost while the original premise still holds.
- **Adopt a Rust core instead when a trigger fires.** Kept open rather than rejected. Should this
  item be reopened, the Rust option is evaluated alongside Kotlin Multiplatform, since the binary
  cost that ruled it in favor of neither may look different at that point.

## Progress

- [ ] Deferred. Monitor the three trigger conditions; no work until one fires.
- [ ] Track SDK core line count in continuous integration, so trigger 1 is observed rather than
      estimated.
- [ ] Label defects traced to cross-platform behavioral differences, so trigger 2 is countable.

## References

- [BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) — the decision this item reopens, and the
  reasoning it rests on.
- [`docs/04-client-sdk.md`](../../docs/04-client-sdk.md) — the SDK design and its size and startup
  budgets.
- [`spec/bucketing.md`](../../spec/bucketing.md) — the specification that holds agreement today, and
  would continue to under either outcome.
