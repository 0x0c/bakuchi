**English** · [日本語](08-operations-ja.md)

# 08. Operations

## 1. Service level objectives

| Service | Indicator | Objective | Error budget |
|---|---|---|---|
| config-edge | Availability as the device sees it, including the CDN | 99.99% | 4.3 minutes a month |
| config-edge | p99 latency | < 150 ms | — |
| Configuration propagation | From publication to every edge | < 60 seconds, at the 99th percentile | — |
| event-gateway | Acceptance rate (2xx) | 99.9% | 43 minutes a month |
| stats-service | Daily results refreshed | By 09:00 JST, at the 99th percentile | — |
| SDK | Main-thread time in `start()` | p99 < 10 ms | — |
| SDK | Configuration fetch success rate | > 98% within 24 hours | — |

**How the error budgets are used:** once config-edge exhausts its budget, publishing new experiments
stops and stabilization takes priority. An overrun on the event pipeline only delays analysis, so it
does not stop publication. Write that asymmetry down.

## 2. Releases

### Server

| Target | Method |
|---|---|
| config-edge, event-gateway | Canary at 1% → 10% → 50% → 100%, 15 minutes per step, rolling back automatically when the indicators go wrong |
| Control plane | Rolling. Traffic is small and brief degradation is acceptable |
| stats-service | Blue-green. **When the statistical logic changes, compute the same experiment on both versions and verify the difference before switching** |
| config-builder | Every change is verified in staging against **a diff of the generated output** (§4) |

### SDK

Releasing an SDK differs fundamentally from releasing a server: **once it is out, it cannot be taken
back** (constraint C2).

1. One week on an internal dogfooding build.
2. One week distributed internally, through TestFlight or an internal testing track.
3. A staged release — App Store Phased Release or Play Staged Rollout — from 1% to 100%, over at least five days.
4. At each step, watch the SDK's own health metrics: initialization success rate, fetch success rate, and crash rate.

**Every SDK ships with a remote kill switch.** A `sdk_kill: {min_version: "1.4.0", action:
"disable_all"}` entry in the configuration disables the SDK itself and drops every experiment to its
default. When a bug turns up in the SDK, that switch is the only way to stop the damage without
waiting for an app release.

## 3. Publishing and rolling back configuration

```
Publish:  draft → validate → preview the diff → approve → build → put to S3 → swap the pointer → purge the CDN
Roll back: point at the previous version → purge the CDN    (seconds)
```

- Configuration objects are immutable, and every version from the last 90 days is retained.
- Swapping the pointer is the only mutable operation. It is atomic, and no partially applied state exists.
- **A rollback needs no approval.** Unless stopping is made as cheap as possible, someone will hesitate in an emergency.

## 4. Showing the diff before publication

Before publishing, config-builder computes the following and displays it in the console. **No other
mechanism prevents as many accidents.**

| What is shown | Why it matters |
|---|---|
| The estimated share of users whose assignment changes | Prevents the accident where "we only raised the allocation" reshuffles everyone |
| The list of experiments affected | Shows the knock-on effect on other experiments sharing the layer |
| The change in bundle size | An early warning before the limit is hit |
| App versions newly in scope | Confirms that an unknown flag is not being delivered to an old version |

## 5. On-call and the runbook

| Alert | First response |
|---|---|
| config-edge availability drops | Check whether the CDN's `stale-if-error` is holding. If it is, lower the urgency and investigate the origin |
| Configuration fetch success rate drops, as seen from the SDK | Check whether it concentrates in a particular SDK version, country, or carrier. If it does, suspect the configuration's contents |
| A guardrail halt fires | The experiment is already stopped, so urgency is low. Check whether it was a false positive and revisit the threshold if so |
| A sample ratio mismatch is detected | Notify the experiment's owner. The experiment is not halted automatically, since running it on only wastes data rather than causing harm, but its results stay hidden |
| Kafka lag grows | Check the headroom in the gateway's spool, then treat it as an analysis delay at medium urgency |
| The A/A false-positive rate departs from its nominal level | **Stop publishing new experiments** and investigate the statistical logic and the pipeline |

**The last resort in an emergency:** `POST /v1/kill-all`, which drops every experiment to control. It
requires two approvals; running it marks every experiment `halted`, and every user gets the default
behavior from their next launch.

## 6. Managing the flag lifecycle (the answer to C2)

Flags cannot be deleted on mobile. Left alone, hundreds accumulate and the configuration bloats.

| Measure | Contents |
|---|---|
| A mandatory expiry | `planned_end_at` is required at creation, and the owner is notified weekly once it passes |
| An inventory dashboard | Lists flags still present more than 90 days after being `completed` |
| A deletion-readiness signal | A flag is marked a deletion candidate once the oldest app version referencing it falls below 1% active share |
| Detection in the code | The SDK bundles a static analyzer for flag keys, and continuous integration warns about code referencing a key absent from the configuration |
| The reverse direction | Flags present in the configuration but referenced by no code are also detected and marked as deletion candidates |

## 7. Security

| Item | Countermeasure |
|---|---|
| Leaked app key | Assumed, since it can be extracted from the binary. Protected by write-only access, rate limiting, and anomaly detection |
| Tampered configuration | An Ed25519 signature, with two keys embedded in the app for rotation |
| Exposure of unannounced features | **The configuration reaches the client whole, which makes it public information.** The operating rule bans code names in experiment keys, and a pre-release feature gets a different name in the configuration too |
| Access control | Publishing an experiment is restricted through role-based access control (RBAC), and `publish` and `kill-all` in production belong to a separate role |
| Auditing | Every change is recorded in `experiment_audit`, which is append-only and replicated to an S3 bucket in a different account |
| Unauthorized console access | Single sign-on with multi-factor authentication, both required |
| Abuse of event ingestion | Anomalous submission from a single address or a single `install_id` is detected and blocked. Assume an attacker who wants to distort the statistics |

## 8. Cost

At 10 million monthly active users and a billion events a day, the event pipeline dominates.

| Item | Relative share | How to reduce it |
|---|---|---|
| ClickHouse storage and compute | ~50% | `LowCardinality` throughout, a 400-day time to live, and per-bucket pre-aggregation that avoids scanning raw data |
| Kafka | ~20% | Shorten retention to three days, since S3 holds the truth and long retention buys nothing |
| CDN transfer | ~15% | Raise the share of 304 responses through disciplined ETag use, and cap the configuration size |
| Compute on Kubernetes | ~10% | Small in practice, because the CDN absorbs config-edge's load |
| S3 | ~5% | Parquet with Iceberg, tiering into Glacier |

**Thinning the events reduces cost more than anything else.** Sampling `reason != ASSIGNED`
exposures at 1% ([chapter 04 §6](04-client-sdk.md#6-exposure-events)) and not sending debug events
in production are design-time decisions, and they move the operating cost by a factor of ten.

## 9. Onboarding and the organization

Building the technical platform alone does not grow a culture of experimentation. Treat the
following as part of the platform.

| Measure | Contents |
|---|---|
| Experiment templates | Per category — validating a new feature, improving performance — a template with the required metrics and guardrails already filled in |
| Pre-registration | The hypothesis, the primary metric, the minimum detectable effect, and the decision criteria are required before an experiment starts. The purpose is **to make the metric unchangeable afterward** |
| Result review | Completed experiments are reviewed weekly, which lets the organization catch misreadings of the statistics |
| Measuring the experiment success rate | Track what share of experiments produced a significant improvement. A healthy organization sits at 10 to 30%, and an extreme figure suggests the statistics are broken |
| Documentation | Write down the common mistakes — peeking, segment fishing, ignoring a sample ratio mismatch — and link to them from the console |
