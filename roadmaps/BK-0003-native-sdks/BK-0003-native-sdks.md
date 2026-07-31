**English** · [日本語](BK-0003-native-sdks-ja.md)

# BK-0003 — Ship native iOS and Android SDKs, guaranteed by golden vectors

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0003](BK-0003-native-sdks.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Accepted** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0003%22) |
| Topic | Client SDK architecture |
| Related | [BK-0007](../BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core.md) |
<!-- /BK-METADATA -->

## Introduction

iOS and Android both need a software development kit (SDK) that behaves identically. When the two
diverge on assignment, experiment results become quietly wrong: no exception is raised, no test
fails, and the numbers still look plausible. The question is how to guarantee that they agree.

This item ships two separate native implementations, one in Swift and one in Kotlin, and guarantees
their agreement with a normative specification plus a shared set of golden vectors rather than with
shared code.

## Motivation

The instinctive answer is to share the logic — a Kotlin Multiplatform core, or a Rust core behind
generated bindings — so that one implementation serves both platforms. Sharing code is the standard
remedy for the standard problem of two implementations drifting apart. Three facts argue against it
here.

**The part that must not drift is small.** Only the deterministic assignment has to agree exactly,
and it is a few dozen lines: a SHA-256 digest, a big-endian read of four bytes, and a cumulative
range scan. Shared code guarantees that the same code runs on both platforms. Golden vectors
guarantee that the same *answer* comes out. The second property is the one we actually want, and a
test asserts it directly rather than by proxy. During the design of this platform, three
independent implementations in Python, Node, and Go were confirmed to reproduce the same vectors,
which is evidence that a specification plus vectors is sufficient to hold agreement across
languages.

**Binary size is not a negotiable requirement.** Telling an iOS team that adding the experimentation
SDK grows the application by 3 MB gets the SDK rejected. The Kotlin/Native runtime is hard to
justify for a component that is not part of the app's value to a user, and an SDK that is never
adopted has no value at all.

**The rest of the SDK cannot be shared anyway.** Caching, event delivery, and background work depend
on mechanisms that differ entirely between the platforms: background upload runs through
`URLSession` on iOS and `WorkManager` on Android; persistence uses the file system with Keychain on
one side and DataStore with encrypted preferences on the other; lifecycle signals come from
different frameworks. What remains genuinely shareable is a thin orchestration layer, which does not
repay the cost of a cross-platform toolchain.

## Detailed design

### The options weighed

| Option | iOS binary growth | Logic sharing | Adoption barrier |
|---|---|---|---|
| **Native, two implementations (Swift and Kotlin)** | around 200 KB | none; held by specification and tests | low |
| Kotlin Multiplatform | plus 1.5 MB to 3 MB | yes | high; needs the iOS team's agreement |
| Rust core with generated bindings | around 400 KB | yes | medium to high; complex build, fewer engineers |

### Platform choices

| Item | iOS | Android |
|---|---|---|
| Language | Swift 5.9 or later, strict concurrency | Kotlin 2.0 or later |
| Minimum support | iOS 15 | API 24 |
| Distribution | Swift Package Manager, with CocoaPods alongside | Maven Central (AAR) |
| Persistence | file system, plus Keychain for `install_id` only | DataStore, plus encrypted preferences |
| Networking | `URLSession`, no dependency | `OkHttp`, which most apps already carry |
| Background delivery | `URLSession` background configuration | `WorkManager` |

**The SDK carries no third-party dependencies.** Version conflicts with the host application are the
single largest barrier to adoption, so avoiding them is treated as a hard constraint rather than a
preference. That constraint also settles the hash choice in
[BK-0004](../BK-0004-bucketing-hash/BK-0004-bucketing-hash.md): SHA-256 is available from the
platform's own cryptography framework at no cost.

### The controls that make this decision safe

Without every control below, two native implementations are merely two chances to be wrong.

1. [`spec/bucketing.md`](../../spec/bucketing.md) is **normative**. Implementations follow it rather
   than each other.
2. Every implementation verifies [`spec/golden-vectors.json`](../../spec/golden-vectors.json) in
   continuous integration, and **a mismatch blocks the merge**.
3. The vectors record intermediate values (`sha256_prefix_hex` and `uint32_be`) as well as the final
   bucket, so a failure identifies *where* the implementation diverged rather than only that it did.
4. Adding a targeting operator updates **both implementations in the same pull request**. A state
   where only one platform has an operator is not allowed to exist.
5. Both implementations carry forward-compatibility tests: an unknown flag type, an unknown variant,
   and an unknown operator must resolve to the caller's default rather than crash.

## Alternatives considered

- **Kotlin Multiplatform with a shared core.** Rejected on binary size and on the ergonomics of the
  generated Swift surface, not on the merits of the technology. The trigger conditions for revisiting
  it are recorded in [BK-0007](../BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core.md)
  rather than left to be re-argued.
- **A Rust core with generated bindings.** Smallest binary and strongest performance, but the build
  pipeline (an `xcframework` plus Android NDK artifacts) and the narrower pool of engineers who can
  maintain it outweigh the gain at this scale.
- **Share only the assignment function, as a tiny library.** Rejected because a few dozen lines do
  not justify a cross-platform build, and the golden vectors already cover exactly that surface.

## Progress

- [ ] Swift SDK: synchronous evaluation, caching, exposure events, debug menu (Phase 1).
- [ ] Kotlin SDK: the same surface (Phase 1).
- [ ] Golden-vector conformance wired into both platforms' continuous integration (Phase 1).
- [ ] Binary-size and startup-time regression gates: 300 KB and 10 ms (Phase 1).

## References

- [`docs/04-client-sdk.md`](../../docs/04-client-sdk.md) — the full SDK design.
- [`spec/bucketing.md`](../../spec/bucketing.md) — the normative algorithm both implementations
  follow.
- [`tools/verify_vectors.py`](../../tools/verify_vectors.py) — the conformance checker.
- [BK-0004](../BK-0004-bucketing-hash/BK-0004-bucketing-hash.md) — the hash choice, which the
  no-dependency constraint here helps settle.
- [BK-0007](../BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core.md) — the conditions
  under which this decision is reopened.
