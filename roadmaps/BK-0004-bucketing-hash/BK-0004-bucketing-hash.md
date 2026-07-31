**English** · [日本語](BK-0004-bucketing-hash-ja.md)

# BK-0004 — Use SHA-256 for deterministic bucketing

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0004](BK-0004-bucketing-hash.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Accepted** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0004%22) |
| Topic | Assignment & determinism |
| Related | [BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) |
<!-- /BK-METADATA -->

## Introduction

Assignment maps a unit identifier to a bucket in the range 0 to 9999, and a variant owns a range of
buckets. The mapping must be reproducible in Swift, Kotlin, Go, Python, and TypeScript, because
[BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) puts the assignment logic in all
of them. This item fixes the hash function that mapping uses.

The choice is effectively irreversible. Changing the hash reshuffles every user, which invalidates
every experiment running at the time, so it can only be done with no experiments in flight.

## Motivation

Speed is the obvious criterion and the wrong one. MurmurHash3 is roughly fifty times faster than
SHA-256, and both are irrelevant at the volume involved: evaluating fifty flags at launch costs
about 25 microseconds with SHA-256, which is a quarter of one percent of the 10 ms budget for
`start()`. No user can perceive the difference, and no benchmark of the SDK would surface it.

The criterion that matters is **implementation uniqueness**: given the same input, does every
language's standard implementation produce the same bytes, without the author having to choose
among variants? MurmurHash3 fails that test. It comes in `x86_32`, `x86_128`, and `x64_128`
variants that disagree on the same input, and implementations differ in how they read the seed and
handle trailing bytes. Optimizely and GrowthBook both use MurmurHash3 x86_32, which makes it look
like an industry default, but that choice was driven by execution speed in a browser and does not
transfer to a mobile app.

Holding five language implementations of MurmurHash3 in agreement, and keeping them in agreement as
each language's ecosystem evolves, is a standing risk taken on in exchange for a speed difference
nobody can measure.

## Detailed design

### The algorithm

```
bucket(salt, unit_id):
    input  := UTF-8( salt + ":" + unit_id )
    digest := SHA-256(input)
    n      := uint32_big_endian(digest[0..4])
    return n mod 10000
```

The normative statement, with per-language reference implementations, lives in
[`spec/bucketing.md`](../../spec/bucketing.md).

### Why each element

| Element | Choice | Reason |
|---|---|---|
| Hash | SHA-256 | present in every language's standard library, with no variants to choose among |
| Separator | `:` | fixes the boundary, so `("ab", "c")` and `("a", "bc")` cannot collide |
| Byte extraction | first four bytes, big-endian | both terms are unambiguous in every language; little-endian invites environment-dependent mistakes |
| Bucket count | 10000 | allocation in units of one basis point |

Availability from the platform's own framework also matters because
[BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) forbids third-party dependencies in the
SDK. `CryptoKit` on iOS and `MessageDigest` on Android both provide SHA-256 at no cost, whereas
MurmurHash3 would mean either hand-rolling it, which is the risk above, or taking a dependency,
which the constraint forbids.

### Cryptographic strength is not the reason

Predicting an assignment is not a threat we defend against, because the configuration is public
under [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) and anyone can compute
their own bucket. SHA-256 is chosen for implementation uniqueness. Recording that distinction here
prevents a future reader from concluding that a faster hash would be safe as long as it were
"secure enough".

### The failure mode this choice creates

Java and Kotlin have no unsigned 32-bit integer, so reading the digest with `ByteBuffer.getInt()`
yields a negative value for about half of all inputs, and Java's `%` carries the dividend's sign.
A 50/50 experiment then splits roughly 75/25, silently. The specification requires the unsigned
read, and the golden vectors carry `uint32_be` precisely so that continuous integration catches
this mistake at the point where it happens.

## Alternatives considered

- **MurmurHash3 x86_32**, the choice of Optimizely and GrowthBook. Rejected on variant ambiguity, as
  argued under Motivation. Its speed advantage is real and irrelevant here.
- **MD5.** Unique in implementation and faster than SHA-256, but prohibited in FIPS-validated
  environments, which would make the SDK unusable for some host applications. SHA-256 has no such
  restriction.
- **Rejection sampling to remove modulo bias.** The bias is `7296 / 2^32`, about 1.7 parts per
  million: assigning a hundred million users skews the split by an expected 0.17 users, which
  changes no test statistic. Correcting it adds branching that each language must reproduce
  identically, so the correction would create more divergence risk than the bias it removes.
- **A larger bucket count, such as one million.** Rejected because allocation finer than one basis
  point has no operational use, and a wider range does not reduce the modulo bias enough to matter.

## Progress

- [x] Algorithm specified in [`spec/bucketing.md`](../../spec/bucketing.md).
- [x] Golden vectors generated and cross-verified across Python, Node, and Go.
- [x] Conformance checker ([`tools/verify_vectors.py`](../../tools/verify_vectors.py)) covering the
      vectors, distribution uniformity, and re-randomization independence.
- [ ] Swift and Kotlin implementations verified against the same vectors (Phase 1).

## References

- [`spec/bucketing.md`](../../spec/bucketing.md) — the normative specification.
- [`spec/golden-vectors.json`](../../spec/golden-vectors.json) — 24 bucket vectors and 15 assignment
  vectors, including empty, non-ASCII, and long unit identifiers.
- [BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) — the no-dependency constraint that
  supports this choice.
