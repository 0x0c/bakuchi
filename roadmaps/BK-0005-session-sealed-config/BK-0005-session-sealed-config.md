**English** · [日本語](BK-0005-session-sealed-config-ja.md)

# BK-0005 — Seal the configuration for the session, apply updates from the next launch

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0005](BK-0005-session-sealed-config.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Accepted** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0005%22) |
| Topic | Client SDK architecture |
| Related | [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) |
<!-- /BK-METADATA -->

## Introduction

The software development kit (SDK) fetches configuration in the background. The question this item
settles is **when a newly fetched configuration takes effect**.

We adopt session sealing: the configuration loaded at launch is used until the session ends, and a
configuration fetched during the session is written to disk and applied from the next launch.

## Motivation

Applying a new configuration the moment it arrives looks harmless and is not. A user can be
assigned to control on the home screen and to treatment two screens later, within one session. The
user interface changes under the user, and — more damaging — **that user is now exposed to both
variants of the same experiment**.

Exposure uniqueness is a precondition of the statistics rather than a nicety. Counting a
both-exposed user as control biases the estimate; counting them as treatment biases it the other
way; dropping them introduces selection bias, because the users who were online during a
configuration change are not a random sample. No downstream analysis recovers from this, and the
corruption is invisible: the numbers still look like numbers.

The cost on the other side is small. Mobile sessions typically run a few minutes, and the next
launch usually arrives the same day. A kill switch also takes effect at the next launch, which is
sufficient, because **a user whose app is not running is not being affected by the experiment in
the first place**. Starting and stopping experiments are operations measured in hours or days; they
do not need minute-level immediacy.

## Detailed design

### What we adopt

The configuration loaded during `start()` is published as an immutable `SealedConfig` and used for
the whole session. A background fetch validates the result and writes it to disk without touching
the sealed snapshot. Returning to the foreground after 30 minutes or more in the background starts
a new session and reseals.

Making `SealedConfig` an immutable object swapped atomically removes every lock from the evaluation
path. That is what lets `variant()` be called from any thread within the 10 ms startup budget, and
it is a consequence of this decision rather than a separate design goal.

The decision also removes the need to push configuration over a persistent connection, since
instant delivery would have no one to serve. Avoiding a held-open socket saves the battery and
connection-management cost that a mobile push channel carries.

### Costs this decision accepts

Sealing makes the cold-start gap visible rather than hiding it. Immediate application could paper
over a first launch by fetching and applying at once; sealing cannot. The answer is a default
configuration compiled into the binary, and an operating rule that follows from it: **an experiment
that must take effect during the first session must be present in the configuration at the time
the release build is produced.** Continuous integration snapshots the current configuration into
the release build to make that possible. Every exposure carries `config_source`, so analysis can
separate users evaluated against a bundled configuration from the rest.

Sealing is also inconvenient during QA, since a configuration change needs a relaunch. The debug
menu's forced reload exists for that reason, and it is the one place where this rule may be broken
deliberately.

### Exceptions

| Case | Handling |
|---|---|
| `sdk_kill`, disabling the SDK itself | **applied immediately**; when the SDK has a serious defect, stopping it outweighs consistency |
| Forced reload from the debug menu | applied immediately, for QA; behind an internal-identity check in release builds |
| Returning to the foreground after 30 minutes or more | treated as a new session and resealed; exposure is recorded against the new session, so uniqueness holds |

## Alternatives considered

- **Apply immediately.** Rejected because it breaks exposure uniqueness, which is a precondition of
  the statistics. The interface flicker is the visible symptom; the invalid experiment is the actual
  cost.
- **Apply at a safe point the app declares,** such as a screen transition. Rejected because the app
  developer has to judge which points are safe, and a wrong judgment produces exactly the
  immediate-apply failure. It also complicates the SDK surface, which raises the chance of incorrect
  use.
- **Block the app at launch until the fetch completes,** so the newest configuration always applies.
  Rejected because it degrades startup time for every user and fails worst for users on weak
  connections, who are already the least well served.

## Progress

- [ ] `SealedConfig` as an immutable snapshot with atomic replacement (Phase 1).
- [ ] Bundled default configuration, and a build step that snapshots the current configuration into
      the release build (Phase 1).
- [ ] `config_source` recorded on every exposure event as `bundled`, `cached`, or `fetched`
      (Phase 1).
- [ ] Forced reload in the debug menu, gated to internal identities in release builds (Phase 1).

## References

- [`docs/04-client-sdk.md`](../../docs/04-client-sdk.md) — the startup sequence and the threading
  model this decision produces.
- [`docs/01-requirements.md`](../../docs/01-requirements.md) — constraint C6, the cold-start gap.
- [`docs/07-statistics.md`](../../docs/07-statistics.md) — why exposure is the denominator, and what
  breaks when it is not unique.
- [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) — local evaluation, which this
  decision assumes.
