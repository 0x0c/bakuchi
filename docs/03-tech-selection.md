**English** · [日本語](03-tech-selection-ja.md)

# 03. Technology selection

Every selection below states what it optimized for. A choice with no trade-off is not recorded here.

## 0. First: should we build this at all?

Settle that question before anything else. **Below a million monthly active users and fewer than
fifty experiments a year, building this platform does not pay for itself.** Start with GrowthBook,
which is open source and self-hostable, or with Firebase A/B Testing. The criteria behind that
judgment are in [BK-0001](../roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy.md).

Everything that follows assumes the decision came out as "build".

---

## 1. Client SDK

### The options

| Option | Implementation | Advantages | Disadvantages |
|---|---|---|---|
| **A. Two native implementations** | Swift and Kotlin | An API that feels natural on each platform. The smallest binary growth. No resistance at adoption. Straightforward debugging | The logic exists twice, which risks divergence between the implementations |
| B. Kotlin Multiplatform | A shared core with a thin native layer | One copy of the logic. Almost no extra cost on Android | The Kotlin/Native runtime lands in the iOS binary, adding 1.5 to 3 MB. The Swift API turns awkward, bridging suspend functions and losing generics. Hard to get the iOS team to agree |
| C. A Rust core with UniFFI | A shared core with generated bindings | The smallest binary, the best performance, one copy of the logic | Someone has to write Rust, and the build pipeline gets complicated (xcframework, Android NDK) |

### Selected: **A, two native implementations, with conformance tests over golden vectors**

The reasons:

1. **What we actually want to share is deterministic assignment, and it is only a few dozen lines** — SHA-256 and a big-endian read. Verifying the [golden vectors](../spec/golden-vectors.json) in every implementation's continuous integration is more direct and more forceful than protecting those lines behind a shared library. While drafting this design we confirmed identical results across three implementations, in Python, Node, and Go.
2. **Constraint C8, binary size, is not negotiable.** "Adding an A/B testing SDK grows the app by 3 MB" gets rejected by the iOS team, and an SDK nobody adopts is worth nothing.
3. The remaining logic — caching, the event queue, retransmission — leans heavily on platform facilities, so sharing it buys less than expected. iOS uses background transfers on `URLSession` and Android uses `WorkManager`; those cannot be shared in the first place.

**The conditions for revisiting, stated up front:** we reevaluate option B if the SDK grows past
5,000 lines, or if two or more bugs trace back to behavioral differences between the two
implementations.

| Item | iOS | Android |
|---|---|---|
| Language | Swift 5.9+ with strict concurrency | Kotlin 2.0+ |
| Minimum supported version | iOS 15 | API level 24 |
| Distribution | Swift Package Manager, with CocoaPods alongside | Maven Central (AAR) |
| Persistence | Files plus the Keychain, which holds only `install_id` | DataStore plus EncryptedSharedPreferences |
| Networking | `URLSession`, with no dependencies | `OkHttp`, which most apps already carry |
| Asynchrony | `async/await` plus a synchronous evaluation API | Coroutines plus a synchronous evaluation API |
| Background transmission | A background `URLSession` configuration | `WorkManager` |

**Carrying no third-party dependencies** is a hard constraint. A version clash with the host app is
the single largest obstacle to adopting an SDK.

---

## 2. Server-side languages

| Service | Language | Reason |
|---|---|---|
| config-edge, event-gateway, assignment-service | **Go** | Fast startup and a small memory footprint, which matter under autoscaling. Garbage-collection tail latency fits the p99 requirement. An HTTP server needs only the standard library, so dependencies stay few |
| experiment-service, metric-service, config-builder | **Go** | Keeping the same language as the data plane lets the assignment logic be **one and the same code**. Splitting it across languages makes determinism hard to guarantee |
| stats-service, metric-aggregator | **Python 3.12** | Not negotiable. The work needs `statsmodels`, `scipy`, and `numpy`, and reimplementing statistical methods in Go would be a mistake |
| console | **TypeScript with Next.js** | Listing experiments and viewing results is ordinary create-read-update-delete work plus dashboards, and the React ecosystem's charting libraries carry most of it |

**Why not Kotlin on the Java virtual machine, or Node, on the server:** startup time and memory put
the JVM at a disadvantage against config-edge's requirement to autoscale into sudden spikes, and
Node's single thread becomes the bottleneck in the CPU-bound parts of event ingestion, validation
and compression. Even so, **an organization already standardized on the JVM is right to unify on
Kotlin and Spring** — operability outweighs a language's technical edge.

---

## 3. Data stores

| Purpose | Selected | The alternative, and why it was rejected |
|---|---|---|
| Experiment metadata | **PostgreSQL 16** | MySQL would work too. PostgreSQL wins on holding targeting conditions in `jsonb` and on managing layer capacity through an exclusion constraint |
| Configuration delivery | **S3 plus a CDN**, with Redis as a hot cache | Reading a database directly does not reach the availability target. Reducing delivery to serving a static file is the sturdiest option |
| Sticky assignment | **Redis**, persisted to DynamoDB or PostgreSQL | Small records, read and written often, and they need a time to live |
| Event bus | **Kafka**, through MSK or Confluent Cloud | Kinesis would work. Kafka wins on flexible partition counts and on how well-worn its connection to Flink is |
| Event analysis | **ClickHouse** | **An existing BigQuery or Snowflake deployment should be used instead.** For a new deployment, ClickHouse: column-oriented, dramatically more cost-efficient on the scan-heavy queries experiment aggregation produces, and self-hostable |
| Raw log storage | **S3**, in Parquet or Iceberg | The single source of truth for reprocessing. ClickHouse is treated as derived data that can be rebuilt |

**A caveat on choosing ClickHouse:** its operational burden is clearly higher than Snowflake's or
BigQuery's, covering replication, merges, and disk management. Without someone dedicated to it, the
total cost is lower on a data warehouse. The organization's situation can reverse this choice.

---

## 4. Stream processing

| Option | Assessment |
|---|---|
| **Flink** (selected) | Event-time windows, **first-class support for late arrivals**, and stateful deduplication. It meets constraint C4 directly |
| Kafka Streams | Requires the JVM. Lighter than Flink, but weaker with late data |
| A simple Go consumer inserting straight into ClickHouse | **Good enough for Phase 1.** Deduplication falls to ClickHouse's `ReplacingMergeTree`. Flink arrives once recomputing late data becomes a problem |

Introducing Flink in Phase 1 is overkill, and worth it only with a team already able to operate it.

---

## 5. Infrastructure

| Item | Selected | Notes |
|---|---|---|
| Container platform | Kubernetes (EKS) | For config-edge alone, something simpler such as ECS Fargate or Cloud Run would also do |
| CDN | CloudFront or Fastly | It must support `stale-if-error` and immediate purges. Fastly purges faster (under a second), which helps if the time for an experiment to take effect needs shortening |
| Continuous delivery | Argo CD (GitOps) | Experiment definitions live in the database, but **metric definitions live in Git** and go through pull-request review |
| Monitoring | OpenTelemetry into Prometheus, Grafana, and Tempo | The SDK reports client-side metrics too: fetch success rate and initialization time |
| Secrets | AWS Secrets Manager with the External Secrets Operator | |
| Infrastructure as code | Terraform | |

---

## 6. Summary of the selection

```
Client       : Swift (SPM) / Kotlin (AAR) — no dependencies, held identical by golden vectors
Data plane   : Go — config-edge / event-gateway / assignment-service
Control plane: Go (experiment / metric / builder) + Next.js (console)
Analysis     : Python + FastAPI (stats), Flink or a Go consumer (stream)
Stores       : PostgreSQL / Redis / Kafka / ClickHouse / S3
Delivery     : S3 + CDN (immutable objects plus a pointer swap)
```

## 7. Deliberately not selected

| Rejected | Reason |
|---|---|
| GraphQL toward the SDK | It cannot be cached at the CDN. A single GET is the right shape for configuration delivery |
| Pushing configuration over WebSocket or server-sent events | Holding a connection open on mobile costs more in battery and connection management than it returns. Taking effect at the next launch is enough ([BK-0005](../roadmaps/BK-0005-session-sealed-config/BK-0005-session-sealed-config.md)) |
| Server-side evaluation as the main path | [BK-0002](../roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation.md) |
| Firebase Remote Config as the delivery layer | Delivery alone gets easier, but layer exclusion, sticky assignment, and consistent exposure logging all fall back to our own implementation, which leaves two systems to keep in step |
| gRPC-Web or Connect toward the SDK | On mobile they add little over HTTP and JSON, and they cost CDN compatibility |
| Exactly-once semantics | At-least-once plus idempotent removal by `event_id` suffices, and exactly-once does not justify its cost |
