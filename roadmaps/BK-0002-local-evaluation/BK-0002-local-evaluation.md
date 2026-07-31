**English** · [日本語](BK-0002-local-evaluation-ja.md)

# BK-0002 — Evaluate assignments on the device, not on the server

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0002](BK-0002-local-evaluation.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Accepted** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0002%22) |
| Topic | Config delivery |
| Related | [BK-0005](../BK-0005-session-sealed-config/BK-0005-session-sealed-config.md), [BK-0008](../BK-0008-config-bundle-signing/BK-0008-config-bundle-signing.md) |
<!-- /BK-METADATA -->

## Introduction

Deciding which variant a user sees can happen in one of two places. Under **remote evaluation** the
app asks a server at launch — "here is who I am, tell me my flags" — and the server answers with
the resolved assignments. Under **local evaluation** the server publishes the whole configuration,
every experiment's definition and targeting rules, and each device decides for itself.

This item adopts local evaluation as the primary path for mobile. Server-side evaluation survives
only for backend experiments and for cross-device sticky assignment, never as the path a mobile app
depends on at launch.

## Motivation

The decision follows from a property of mobile apps that has no counterpart on the web: **a shipped
binary cannot be rolled back by deploying.** Reverting broken code means submitting a new build and
waiting for store review, then waiting again for users to update. Until that completes, the only
way to stop a misbehaving experiment is a remote kill switch.

Configuration delivery is therefore not a convenience feature. It is the sole emergency stop for
every experiment in the app, which makes **its availability the app's availability**. Any argument
about which evaluation model to adopt must be settled on that basis first.

Remote evaluation puts that critical path behind a dynamic application server that must resolve
targeting rules per request. Local evaluation reduces it to a static file on object storage fronted
by a content delivery network. The gap between those two availability profiles is large enough to
outweigh every other consideration, and the rest of this item is about paying the resulting costs
rather than about weighing the choice again.

Two further consequences follow, both of which favor local evaluation independently. Evaluation
becomes synchronous and free of network latency, so a flag can be read on the UI thread without an
`await`. And the app keeps working offline, which matters because a meaningful share of mobile
sessions begin with no usable connection.

## Detailed design

### The two options

| | Remote evaluation | Local evaluation |
|---|---|---|
| Availability profile | dynamic service, per-request targeting | static object on a content delivery network |
| Evaluation latency | one network round trip at launch | none; a pure function over memory |
| Offline behavior | unavailable | fully functional from cache |
| Server-side attributes in targeting | available | only what the app passes in |
| Configuration secrecy | assignments only | the whole configuration reaches the device |
| Assignment logic | one implementation | one per language, requiring conformance testing |
| Request volume at ten million monthly active users | thirty million dynamic requests per day | the same volume, but cacheable, mostly answered `304` |

### What we adopt

Local evaluation for every mobile path. The server publishes an immutable configuration bundle;
`config-edge` serves it with an `ETag`; the software development kit (SDK) caches it, evaluates
against it synchronously, and never blocks the app on a fetch. `assignment-service` provides
server-side evaluation for backend experiments and for sticky assignment that must hold across
devices, and no mobile launch path depends on it.

The resulting failure behavior is the point of the design. When the content delivery network fails,
the SDK keeps using its local cache and app behavior does not change. When the origin fails, the
network keeps serving the last good object under `stale-if-error`. When the database fails, running
experiments are untouched, because the configuration on object storage is self-contained.

### Costs this decision accepts

1. **The configuration is public.** Anyone can extract it from an application package, so experiment
   keys and parameters are public information. Unreleased features must not be identifiable by their
   experiment key, and the naming rule that enforces it lives in
   [`docs/08-operations.md`](../../docs/08-operations.md).
2. **Assignment logic exists in several languages.** [`spec/bucketing.md`](../../spec/bucketing.md)
   is therefore normative, and every implementation is verified in continuous integration against
   [`spec/golden-vectors.json`](../../spec/golden-vectors.json). This cost would not exist under
   remote evaluation, and paying it deliberately is what makes the availability gain affordable.
3. **Server-side data cannot drive targeting.** The app passes attributes to the SDK. Attributes it
   cannot compute, such as an aggregate of purchase history, are precomputed into a segment
   identifier and delivered to the app at login.
4. **The bundle grows over time.** It is split by platform and SDK major version, and its size is
   capped at 100 KB compressed.

## Alternatives considered

- **Remote evaluation as the primary path.** Rejected because it places the app's only emergency
  stop behind a dynamic service. The secrecy and single-implementation benefits are real, but they
  are worth less than the availability difference on a path that cannot be fixed by deploying.
- **Remote evaluation with a local cache as fallback.** Rejected as the worst of both: it still
  needs the dynamic service on the first launch of every install, still ships assignment logic to
  the device for the fallback path, and adds a second code path that is exercised only during
  incidents — precisely when it is least safe to be untested.
- **Push configuration over a persistent connection** so changes apply instantly. Rejected because
  holding a socket open on mobile costs battery and connection management for a benefit that
  [BK-0005](../BK-0005-session-sealed-config/BK-0005-session-sealed-config.md) shows we do not
  want: applying a change mid-session breaks exposure uniqueness.

## Progress

- [ ] `config-edge` serving immutable bundles from object storage behind a content delivery network
      (Phase 1).
- [ ] SDK-side caching, validation, and synchronous evaluation (Phase 1).
- [ ] `assignment-service` for backend experiments and cross-device sticky assignment (Phase 2).

## References

- [`docs/01-requirements.md`](../../docs/01-requirements.md) — constraint C2, the store-review
  rollback delay this decision turns on.
- [`docs/02-architecture.md`](../../docs/02-architecture.md) — the failure table this design
  produces.
- [`docs/05-services.md`](../../docs/05-services.md) — `config-edge`, which holds no database as a
  direct consequence.
- [BK-0005](../BK-0005-session-sealed-config/BK-0005-session-sealed-config.md) — session sealing,
  which assumes local evaluation.
