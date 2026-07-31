**English** · [日本語](BK-0009-flink-late-data-ja.md)

# BK-0009 — Adopt Flink for late-arriving event reprocessing

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0009](BK-0009-flink-late-data.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal (deferred)** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0009%22) |
| Topic | Data pipeline |
| Related | [BK-0006](../BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md) |
<!-- /BK-METADATA -->

## Introduction

Mobile events arrive late. A device with no connection, an operating system that schedules
background uploads on its own terms, and a user who does not open the app for days all push events
past the window in which they were generated. The pipeline in
[`docs/06-data-pipeline.md`](../../docs/06-data-pipeline.md) handles this with a seven-day
watermark and daily recomputation.

Phase 1 implements that with a plain consumer writing into the warehouse, and deduplication left to
the store. This item proposes replacing the consumer with Apache Flink once the simple approach
stops holding, and records what "stops holding" means.

## Motivation

Flink is the technically correct tool for this problem. Event-time windowing, first-class handling
of late arrivals, and stateful deduplication map directly onto the requirement. Adopting it in
Phase 1 anyway would be a mistake, and naming why is the point of deferring rather than rejecting.

A stream processor is a stateful distributed system with its own failure modes: checkpoint storage,
state backend sizing, job restarts that replay, and version upgrades that invalidate savepoints.
Phase 1's goal is a delivery path the team trusts, and adding an operationally demanding component
before the simple one has demonstrably failed spends the team's attention on the wrong risk.

The simple approach is genuinely sufficient for a while. A consumer that writes into a
replacing-merge table, with deduplication by `event_id` and daily recomputation over a trailing
window, produces the same numbers as Flink would as long as the late-arrival share stays small and
the recomputation window stays affordable. What Flink buys is not correctness at that scale; it is
correctness at a scale where daily recomputation over the trailing window becomes too expensive to
run.

## Detailed design

### Trigger conditions

Adopt Flink when **any one** of the following holds:

1. **Daily recomputation over the trailing seven days no longer finishes within its window,** or
   costs more than the incremental processing Flink would replace it with.
2. **The share of events arriving more than 24 hours late exceeds 3% and is sustained,** so that
   correcting after the fact is the dominant cost rather than an edge case.
3. **Deduplication in the store measurably degrades query performance,** for instance because
   merge pressure from the replacing engine outpaces the merge throughput available.

### What adoption looks like

Flink sits between the event bus and the warehouse, taking over deduplication, enrichment, clock-skew
correction, and windowing. The warehouse then receives records that are already deduplicated and
corrected, and the daily recomputation job shrinks to a much narrower correction pass.

The pipeline is arranged so this substitution stays local. Raw events on object storage remain the
single source of truth, so the processor can be swapped and history replayed through the new path
without data loss. That property is why the item can be deferred safely: choosing the simple path
now does not foreclose the sophisticated one later.

### The prerequisite that is not technical

Do not adopt Flink without someone who operates it. The same condition governs
[BK-0006](../BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md), and it fails
the same way: an unowned stateful system degrades quietly, and a pipeline that degrades quietly
produces wrong experiment results rather than an outage. When a trigger fires and no owner exists,
the correct response is to raise the recomputation budget or shorten the watermark, not to adopt
Flink and hope.

## Alternatives considered

- **Adopt Flink in Phase 1**, since it is the right tool. Rejected because Phase 1's goal is a
  trusted delivery path, and a stateful distributed system spends the team's attention on
  operational risk before the simple approach has been shown to fail.
- **Kafka Streams instead of Flink.** Lighter to operate, but its handling of late-arriving data is
  weaker, which is the specific requirement driving this item. Reconsider only if the team is
  already deep in the JVM ecosystem.
- **Never adopt a stream processor; scale the batch recomputation instead.** Kept as the fallback
  when a trigger fires without an owner. It costs more compute and bounds how far the watermark can
  extend, and it keeps the pipeline operationally simple, which is sometimes the better trade.
- **Shorten the watermark to make recomputation cheap.** Rejected as a primary strategy because it
  trades a cost problem for a correctness problem: events past the watermark are discarded, and the
  discarded share is not random across variants.

## Progress

- [ ] Deferred to Phase 3. Phase 1 ships the plain consumer.
- [ ] Instrument the late-arrival distribution as a dashboard, so trigger 2 is observed rather than
      assumed.
- [ ] Track daily recomputation duration and cost, so trigger 1 is observed.
- [ ] Confirm an operator exists before adoption; otherwise take the batch-scaling fallback.

## References

- [`docs/06-data-pipeline.md`](../../docs/06-data-pipeline.md) — the watermark, recomputation
  policy, and deduplication layers this item would replace.
- [`docs/03-tech-selection.md`](../../docs/03-tech-selection.md) — the stream-processing selection
  and its "Phase 1 does not need this" note.
- [`docs/01-requirements.md`](../../docs/01-requirements.md) — constraint C4, late and unordered
  arrival.
- [BK-0006](../BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md) — the sibling
  decision governed by the same ownership condition.
