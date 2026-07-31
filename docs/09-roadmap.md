**English** · [日本語](09-roadmap-ja.md)

# 09. The phased build plan

Do not build everything at once. Each phase is cut so that it **delivers value on its own and can end
there**.

## Phase 0: validation (2 weeks)

Check before building.

- [ ] Against the criteria in [BK-0001](../roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy.md), conclude whether to build this at all
- [ ] Check whether a data warehouse already exists (BigQuery or Snowflake); if one does, do not adopt ClickHouse
- [ ] Estimate the expected event volume and its cost
- [ ] Present the SDK's size and startup-time budgets to the iOS and Android teams and get their agreement
- [ ] Implement the bucketing algorithm exactly as [spec/](../spec/) states, and confirm that four languages agree against the golden vectors

**Phase 0 succeeds even when its conclusion is "do not build".**

---

## Phase 1: feature-flag delivery (6 to 8 weeks)

**The goal is safe flag delivery, not experimentation.** Reliable delivery comes before any
statistics.

| Area | Deliverable |
|---|---|
| SDK | iOS and Android: synchronous evaluation, a local cache, bundled defaults, exposure events, and a debug menu |
| Delivery | config-edge with S3 and a CDN: immutable objects plus a pointer swap |
| Control | experiment-service, metric-service, config-builder, and the console as a **single deployment unit** |
| Events | event-gateway → Kafka → **a simple Go consumer** → ClickHouse. Flink stays out for now |
| Analysis | **Manual aggregation in the existing business-intelligence tools or data warehouse.** No dedicated stats-service yet |

**What this stage can do:** staged rollout, kill switches, and A/B assignment with exposure logging.
Deciding the result is manual SQL.

**What this stage deliberately does not do:** the statistics engine, layer exclusion (there is a
single layer), sticky assignment, and server-side experiments.

**Done when:** one experiment has run to completion in production and a conclusion was drawn by
hand.

---

## Phase 2: becoming an experimentation platform (8 to 10 weeks)

**The goal is automating the statistical decision so that a product manager can run an experiment
unaided.**

| Area | Deliverable |
|---|---|
| Statistics | stats-service: Welch's t-test, proportions, the delta method, and confidence intervals |
| Diagnostics | **The sample-ratio-mismatch test as a hard gate on displaying results**, plus a pre-period A/A check |
| Design support | Sample-size calculation and an up-front estimate of the duration |
| Exclusion | Mutual exclusion through layers, via the database's `EXCLUDE` constraint |
| Safety | Automatic halts from guardrail-watcher, and retention as a mandatory guardrail on every experiment |
| Quality | Two A/A experiments running continuously, and data-quality monitoring ([chapter 06 §8](06-data-pipeline.md#8-data-quality-monitoring)) |
| Server side | assignment-service and the `abkit-go` embedded library |

**Done when:** a product manager can create, start, and decide an experiment without an engineer,
and the A/A false-positive rate sits at its nominal level.

---

## Phase 3: precision and scale (ongoing)

**The goal is raising the throughput and the statistical power of experimentation.**

| Area | Deliverable |
|---|---|
| Variance reduction | CUPED, applied to the existing-user segment |
| Sequential testing | Always-valid confidence intervals through mSPRT, as the dashboard default |
| Multiple comparisons | Benjamini-Hochberg and Dunnett |
| Late data | Adopting Flink, with watermark-based recomputation |
| Quantiles | Latency metrics through t-digest |
| Advanced analysis | Novelty-effect detection, heterogeneous treatment effects, and cluster randomization |
| Operations | Automating the flag inventory, and detecting unused flags through static analysis |
| Holdback | Measuring the effect that accumulates across experiments, through a group permanently excluded from every one |

---

## Candidates for Phase 4 and beyond, decided on Phase 3's record

- Multi-armed bandits, automating the trade-off between exploration and exploitation. Priority stays low, because **introducing them before the culture of experimentation matures multiplies decisions nobody can explain the reason for**
- Personalization, selecting the best variant automatically per segment
- Extensions into causal inference: effect estimation from observational data, and regression discontinuity designs
- Meta-analysis of past results, building priors from the distribution of past effect sizes

---

## Risks and assumptions

| Risk | Response |
|---|---|
| The iOS or Android team does not adopt the SDK | Agree the size and startup-time budgets in Phase 0, and put members of both teams on SDK development |
| Nobody understands the statistics and results get misread | Build the sample-ratio-mismatch hard gate and the explicit "not significant ≠ no difference" wording into the implementation in Phase 2, rather than relying on documentation |
| Phase 1 gets overbuilt | Hold "no statistics engine" as an explicit constraint |
| ClickHouse costs too much to operate | Use the existing data warehouse if one exists. Decide in Phase 0 |
| No experiments run and the platform goes stale | Phase 1's completion criterion is one experiment run end to end. Completion means use, not technical readiness |
