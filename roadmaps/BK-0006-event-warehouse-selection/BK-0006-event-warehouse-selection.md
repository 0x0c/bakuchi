**English** · [日本語](BK-0006-event-warehouse-selection-ja.md)

# BK-0006 — Choose between ClickHouse and the existing data warehouse

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0006](BK-0006-event-warehouse-selection.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0006%22) |
| Topic | Data pipeline |
| Related | [BK-0001](../BK-0001-build-vs-buy/BK-0001-build-vs-buy.md) |
<!-- /BK-METADATA -->

## Introduction

Exposure and metric events land in a store that the statistics layer queries. The technology
selection in [`docs/03-tech-selection.md`](../../docs/03-tech-selection.md) names ClickHouse, with
an explicit caveat: **when the company already runs BigQuery or Snowflake, that warehouse should be
used instead.** This item exists to make that caveat a decision with an owner and a date, rather
than a note that quietly resolves itself the first time someone writes a query.

## Motivation

The choice is easy to defer and expensive to defer, because both directions get harder with time.
Metric definitions, aggregation jobs, and the statistics service all bind to whichever store is
chosen; moving after those exist means rewriting the query layer and backfilling history.

Deferral also tends to resolve by accident. Whoever writes the first aggregation query picks a
store, and that becomes the decision without anyone having compared operating costs. The result is
a store chosen for the convenience of one afternoon rather than for the five years the data will
live in it.

The two options differ in a way that is easy to state and easy to underweight. ClickHouse is
markedly more cost-efficient for the scan-heavy aggregations experiment analysis produces, and it
can be self-hosted. It also carries real operational load: replication, merges, and disk
management. Without someone who owns that load, the total cost of ClickHouse exceeds the total cost
of a managed warehouse even where the compute bill is lower — which is exactly the trade a compute
comparison alone will miss.

## Detailed design

### The decision rule

Decide during Phase 0, alongside [BK-0001](../BK-0001-build-vs-buy/BK-0001-build-vs-buy.md), and
record the outcome in this item.

- **An existing warehouse is in production** (BigQuery, Snowflake, or Redshift) **and** the
  experiment volume fits its cost model → **use it.** Skip ClickHouse. The integration cost of a
  second store, and the risk of two divergent copies of the same events, outweigh the query-cost
  saving.
- **No warehouse exists, and someone owns the operational load** → **adopt ClickHouse.**
- **No warehouse exists, and nobody owns the operational load** → **adopt a managed warehouse.**
  Do not adopt ClickHouse expecting to find an owner later.

### What to measure before deciding

| Input | Why it decides the outcome |
|---|---|
| Existing warehouse and its pricing model | per-scan pricing punishes the scan-heavy queries experiment analysis produces |
| Events per day, and retention | sets the storage bill under either option |
| Who operates the store | the condition ClickHouse fails most often |
| Whether metric definitions already exist in the warehouse | reusing them avoids maintaining two definitions of the same metric |

### What does not change either way

The pipeline is designed so this decision stays local to one layer. Object storage holds the raw
events as the single source of truth, in Parquet under a table format, and the warehouse holds a
derived copy that can be rebuilt. The bucket-level pre-aggregation described in
[`docs/06-data-pipeline.md`](../../docs/06-data-pipeline.md) is expressible in either store, and it
is what keeps the statistics layer from scanning raw events at all.

Keeping the raw events authoritative outside the warehouse is what makes this decision reversible
in principle. Reversing it still costs a rewrite of the query layer, which is why it is worth
deciding once, deliberately, in Phase 0.

## Alternatives considered

- **Adopt ClickHouse unconditionally**, as the technology selection's headline choice. Rejected as
  a standing decision because it ignores the case where a warehouse already exists, where a second
  store adds integration cost and a second copy of the same events.
- **Run both**, with ClickHouse for experiment queries and the warehouse for everything else.
  Rejected because two copies of the same events drift, and reconciling a metric that disagrees
  between stores costs more than either store saves.
- **Defer to Phase 2, once query patterns are known.** Rejected because the metric service and the
  aggregation jobs bind to the store during Phase 1, so by Phase 2 the decision has already been
  made implicitly.

## Progress

- [ ] Inventory the existing warehouse, if any, and its pricing model.
- [ ] Estimate events per day and the resulting storage and query cost under each option.
- [ ] Confirm who operates the store, in writing.
- [ ] Record the decision and its reasoning in this item, then update
      [`docs/03-tech-selection.md`](../../docs/03-tech-selection.md).

## References

- [`docs/03-tech-selection.md`](../../docs/03-tech-selection.md) — the data-store selection and its
  caveat.
- [`docs/06-data-pipeline.md`](../../docs/06-data-pipeline.md) — the schema and the bucket-level
  pre-aggregation, expressible in either store.
- [`docs/08-operations.md`](../../docs/08-operations.md) — the cost breakdown, where this store
  dominates.
- [BK-0001](../BK-0001-build-vs-buy/BK-0001-build-vs-buy.md) — decided in the same phase; the
  warehouse inventory feeds both.
