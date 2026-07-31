**English** · [日本語](01-requirements-ja.md)

# 01. Requirements

## 1. Scope

| In scope | Out of scope (for now) |
|---|---|
| Feature-flag delivery (staged rollout, kill switch) | A visual editor (swapping the user interface without a code change) |
| A/B/n testing, on both the client and the server | Personalization and bandit optimization (revisited in Phase 3) |
| Deterministic assignment of subjects, with mutual exclusion through layers | Push-notification delivery itself |
| Exposure and metric event collection | General business-intelligence dashboards (delegated to the existing tools) |
| Statistical analysis, significance testing, and guardrail monitoring | Mobile measurement partner (attribution) features |

## 2. Actors

| Actor | Main use cases |
|---|---|
| Product manager | Designing, starting, and stopping experiments; interpreting results |
| Client engineer | Integrating the software development kit (SDK), branching on flags, quality assurance |
| Server engineer | Server-side experiments and backend flags |
| Data scientist | Defining metrics, validating statistical methods, deep-dive analysis |
| Site reliability engineer | Kill switches and automatic halts driven by guardrails |

## 3. Functional requirements

### 3.1 Experiment management
- Create, read, update, and delete experiments, with a draft → review → running → stopped → archived lifecycle.
- Variant definitions (`control`, `treatment`, and so on) and per-variant **parameters** in JSON. A flag returns a bundle of typed settings rather than a boolean.
- Targeting conditions: app version, operating-system version, platform, country and language, user attributes, existing segments, and random sampling.
- **Layers (mutually exclusive groups).** Experiments in the same layer never share a subject. Experiments in different layers assign independently and may overlap.
- **Holdback.** A permanent control group excluded from every experiment, which measures the combined effect of every experiment over time.
- Beyond mutual exclusion, the model must express **dependency**: experiment B targets only the treatment group of experiment A.

### 3.2 Assignment
- Assignment is deterministic. The same `(unit_id, experiment, seed)` always yields the same variant, and the server, the client, and the analysis pipeline agree exactly.
- The randomization unit is selectable per experiment: `install_id`, `user_id`, `account_id`, or `session_id`.
- Re-randomizing by updating the seed yields an assignment independent of the previous one.
- **Sticky assignment.** An optional mode keeps a subject on its variant once assigned, even after the subject stops matching the targeting conditions — after the rollout percentage is lowered, for example.

### 3.3 SDK
- The synchronous API always returns a value; after initialization it never returns null.
- Initialization does not block app startup.
- The SDK works offline.
- Exposure events are emitted automatically at evaluation and deduplicated within a session.
- Variants can be forced for quality assurance, through a deep link or a debug menu.

### 3.4 Analysis
- Metrics are aggregated automatically per experiment, and effects are estimated with confidence intervals.
- Sample ratio mismatch (SRM) detection is a **hard gate on displaying results**.
- A guardrail-metric violation raises an alert and halts the experiment automatically.
- Both quantile metrics (p50 and p95 latency, for example) and proportion metrics (conversion rate) are supported.

---

## 4. The mobile-specific constraints at the core of this design

Lifting a web experimentation platform onto mobile unchanged always breaks. The constraints below
are why, and nearly every design decision that follows derives from them.

### C1. Variant code ships inside the binary
Unlike the web, where the server renders the page, a mobile treatment exists **only inside an app
binary that has already been released**. Configuration merely selects which of the code paths
already present the app takes.

**Consequences:**
- The code has to ship before the experiment starts, released ahead of time with the flag off.
- **Version targeting is mandatory**, restricting an experiment to app versions that contain the code.
- When an older app receives an unknown flag or an unknown variant, it **must fall back to the safe side**, the default that corresponds to control. Forward compatibility is a hard requirement on the SDK.

### C2. An app version takes weeks to reach users
Rolling back code means going through store review. A deployment cannot undo it.

**Consequences:**
- A remote kill switch is the only way to stop an experiment in an emergency. The availability of configuration delivery *is* the availability of the app, which puts its service level objective in the highest tier.
- Flags are long-lived: a flag cannot be removed until the oldest supported version is gone. Operations needs a process for retiring flags.

### C3. Mixed app versions confound the result
When a new app version ships during an experiment, the population picks up a biased subgroup: the
users who update early.

**Consequence:** treat app version as a covariate during analysis, or fix the analysis to a single
version. Make the per-version breakdown a standard output.

### C4. Events arrive late and out of order
Users go without signal, background transmission is constrained (the timing of an iOS background
task is up to the operating system), and some users do not open the app for days.

**Consequences:**
- The client keeps events in a persistent queue and retries, giving at-least-once delivery.
- Idempotent deduplication by `event_id` is mandatory on the server.
- The analysis pipeline **recomputes on the assumption that data arrives late**: a seven-day watermark, final at fourteen days.
- "No event" does not mean "the user did nothing", so a heartbeat is needed to tell the two apart.

### C5. Device clocks cannot be trusted
A user can change the clock by hand, and time zones move with the user.

**Consequence:** estimate the skew between the device clock and the server's receive time per batch
and correct for it. Send a monotonic clock (`uptime`) alongside each event to recover the ordering
within a batch.

### C6. Configuration is not there yet at startup
On a first launch, or during a cold start before a fetch completes, evaluation still runs.

**Consequences:**
- Ship a default configuration inside the binary at build time.
- Distinguish, in the specification, an experiment that must take effect from the first session from one that may wait until the second. The first kind can run only from the configuration bundled into the binary, which means it must be settled at release time.
- Record in the exposure's `reason` that evaluation happened before the fetch completed, so that analysis can separate those users.

### C7. Privacy constraints
The identifier for advertisers (IDFA) is unavailable without consent under App Tracking
Transparency, and the Android advertising ID can be opted out of. A device identifier such as
`ANDROID_ID` should not be used at all.

**Consequence:** use an install-scoped identifier the SDK generates itself (`install_id`). The SDK
documents and supplies what the iOS Privacy Manifest (`NSPrivacyAccessedAPITypes`) and the Google
Play Data Safety declaration require.

### C8. App size and startup time are product metrics
A heavy SDK gets rejected.

**Consequences, stated as budgets:** under 300 KB added to the binary after compression, under 10 ms
of main-thread time in `start()`, and under 1 MB of configuration resident in memory.

---

## 5. Non-functional requirements

| Item | Target |
|---|---|
| Configuration fetch latency | p50 < 30 ms, p99 < 150 ms at the content delivery network (CDN) edge |
| Configuration delivery availability | 99.99%, through a CDN plus a static fallback that keeps serving the old configuration even if the origin is entirely lost |
| Time for an experiment to take effect | Under 60 seconds from publication to every edge |
| Time for a kill switch to take effect | At the device's next move to the foreground, so a few minutes in practice |
| Event ingestion availability | 99.9%, favoring acceptance: under backpressure the gateway still returns 202 and spools to disk |
| Event loss rate | Under 0.1%, measured against what the client set out to send |
| Result refresh frequency | Hourly for provisional numbers, daily for final ones |
| Concurrent experiments | 200, including mutual exclusion through layers |
| SDK initialization | Under 10 ms on the main thread, with all input and output asynchronous |

## 6. Explicit non-goals

- **A real-time assignment API is not the main path.** Evaluation happens on the device
  ([BK-0002](../roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation.md)).
- **Exactly-once delivery is not pursued.** At-least-once delivery plus idempotent deduplication
  replaces it, because exactly-once does not justify its cost here.
- **Secrets never appear in the configuration.** The delivered configuration reaches the client whole,
  so every experiment name and parameter counts as public. Operations needs a rule against putting
  the code name of an unannounced feature in there.
